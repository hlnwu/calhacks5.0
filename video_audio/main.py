import os

from flask import Flask, redirect, render_template, request

from google.cloud import storage
from google.cloud import videointelligence
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types


app = Flask(__name__)

class AnalyzeData:
    def __init__(self, key, value, start_time, end_time):
        self.key = key
        self.value = value
        self.start_time = start_time
        self.end_time = end_time

datum = []

@app.route('/')
def homepage():
    # Return a Jinja2 HTML template and pass in image_entities as a parameter.
    return render_template('homepage.html')


# Detects labels given a Google Cloud Storage (GCS) URI.
# Adapted from: https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/video/cloud-client/labels/labels.py
def get_label_annotations(gcs_uri):
    video_client = videointelligence.VideoIntelligenceServiceClient()
    features = [videointelligence.enums.Feature.LABEL_DETECTION]
    operation = video_client.annotate_video(gcs_uri, features=features)

    # Wait until the  annotate_video function call has completed.
    results = operation.result(timeout=90).annotation_results[0]
    label_annotations = results.segment_label_annotations
    return label_annotations

def transcribe_audio(gcs_uri):

    # Create a Speech Client object to interact with the Speech Client Library.
    client = speech.SpeechClient()

    # Create audio and config objects that you'll need to call the API.
    audio = speech.types.RecognitionAudio(uri=gcs_uri)
    config = speech.types.RecognitionConfig(
        encoding=speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code='en-US')

    # Call the Speech API using the Speech Client's recognize function.
    response = client.recognize(config, audio)
    return response

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # Create a Cloud Storage client.
    storage_client = storage.Client()

    # Get the Cloud Storage bucket that the file will be uploaded to.
    bucket = storage_client.get_bucket(os.environ.get('CLOUD_STORAGE_BUCKET'))

    # Create a new blob and upload the file's content to Cloud Storage.
    video = request.files['videofile']
    audio = request.files['audiofile']
    videoblob = bucket.blob(video.filename)
    videoblob.upload_from_string(
            video.read(), content_type=video.content_type)

    audioblob = bucket.blob(audio.filename)
    audioblob.upload_from_string(
            audio.read(), content_type=audio.content_type)
    # Make the blob publicly viewable.
    videoblob.make_public()
    video_public_url = videoblob.public_url

    # Retrieve a Video response for the video stored in Cloud Storage
    videosource_uri = 'gs://{}/{}'.format(os.environ.get('CLOUD_STORAGE_BUCKET'), videoblob.name)
    label_annotations = get_label_annotations(videosource_uri)

    # Add labels and their corresponding information to a class called AnalyzeData
    for label in label_annotations:
        start_time = label.segments[0].segment.start_time_offset.seconds - (label.segments[0].segment.start_time_offset.nanos / 1000000000.0)
        end_time = label.segments[0].segment.end_time_offset.seconds - (label.segments[0].segment.end_time_offset.nanos / 1000000000.0)
        newConfidence = label.segments[0].confidence * (end_time - start_time) / end_time
        analyzeData = AnalyzeData(label.entity.description, newConfidence, start_time, end_time)
        datum.append(analyzeData)
    
    # Sort "data" list by value (AKA confidence)
    def getKey(datum):
        return datum.value

    data = sorted(datum, key = getKey, reverse = True)

    audiosource_uri = 'gs://{}/{}'.format(os.environ.get('CLOUD_STORAGE_BUCKET'), audioblob.name)
    response = transcribe_audio(audiosource_uri)
    results = response.results

    # Redirect to the home page.
    return render_template('homepage.html', video_public_url=video_public_url, video_content_type=video.content_type, label_annotations=label_annotations, data=data, results=results)

@app.errorhandler(500)
def server_error(e):
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
