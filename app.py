from flask import Flask
from flask_restful import Api
from recommend_resources import TherapistRecommendation

app=Flask(__name__)

api=Api(app)


@app.route("/")
def home():
    return "<h1 style='color:blue'>This is the Therapist Details  pipeline!</h1>"


api.add_resource(TherapistRecommendation, '/recommend_therapist')

if __name__=='__main__':
    app.run(port= 5000, debug=True)