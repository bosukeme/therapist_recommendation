from flask_restful import Resource, reqparse
from recommend_therapist import get_recommendations


class TherapistRecommendation(Resource):
    def get(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('language', type=str, help="The language of the user")
            parser.add_argument('ethnicity', type=str, help="The ethnicity of the user")
            parser.add_argument('lgbt', type=str, help="The lgbtq choice of the user")
            parser.add_argument('user_symptoms', type=str, help="the symptoms of the user")

            args = parser.parse_args()



            result = get_recommendations(args['language'], args['ethnicity'], args['lgbt'], args['user_symptoms'])
            return {
                'status': 'success',
                'data': result, 
                'message': 'Therapist recommendation successful.'
            }, 200

        except Exception as e:
            return {
                'status': 'failed',
                'data': None,
                'message': str(e)
            }, 500

