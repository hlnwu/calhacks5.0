# [START video_label_tutorial]
# [START video_label_tutorial_imports]
import argparse
import operator

from google.cloud import videointelligence
# [END video_label_tutorial_imports]


def analyze_labels(path):
    """ Detects labels given a GCS path. """
    # [START video_label_tutorial_construct_request]
    video_client = videointelligence.VideoIntelligenceServiceClient()
    features = [videointelligence.enums.Feature.LABEL_DETECTION]
    operation = video_client.annotate_video(path, features=features)
    # [END video_label_tutorial_construct_request]
    print('\nProcessing video for label annotations:')

    # [START video_label_tutorial_check_operation]
    result = operation.result(timeout=90)
    print('\nFinished processing.')
    # [END video_label_tutorial_check_operation]


    data =dict()

    # [START video_label_tutorial_parse_response]
    segment_labels = result.annotation_results[0].segment_label_annotations
    for i, segment_label in enumerate(segment_labels):
        print('Video label description: {}'.format(
            segment_label.entity.description))
        for category_entity in segment_label.category_entities:
            print('\tLabel category description: {}'.format(
                category_entity.description))

        for i, segment in enumerate(segment_label.segments):
            start_time = (segment.segment.start_time_offset.seconds +
                          segment.segment.start_time_offset.nanos / 1e9)
            end_time = (segment.segment.end_time_offset.seconds +
                        segment.segment.end_time_offset.nanos / 1e9)
            positions = '{}s to {}s'.format(start_time, end_time)
            confidence = segment.confidence
            print('\tSegment {}: {}'.format(i, positions))
            print('\tConfidence: {}'.format(confidence))
            data[segment_label.entity.description] = confidence;
        print('\n')

    # [END video_label_tutorial_parse_response]
    print (data)
    dat= sorted(data,key=data.get,reverse=True)
    for r in dat:
        print (r,data[r])
    print( max(data.items(),key = operator.itemgetter(1))[0])


if __name__ == '__main__':
    # [START video_label_tutorial_run_application]
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('path', help='GCS file path for label detection.')
    args = parser.parse_args()

    analyze_labels(args.path)
    # [END video_label_tutorial_run_application]
# [END video_label_tutorial]
