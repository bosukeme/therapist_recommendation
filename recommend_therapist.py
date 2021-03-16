from pymongo import MongoClient
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
import string


MONGO_URL = "mongodb+srv://bloverse:b1XNYDtSQNEv5cAn@bloverse-production.fbt75.mongodb.net/blovids?retryWrites=true&w=majority"  #os.environ.get("MONGO_URL")

client= MongoClient(MONGO_URL, connect=False)
db = client.bacp_counselling


def get_therapist_from_db():
    '''
        Query the DB and return all the therapist saved there
    '''
    super_pow_therapist_collection = db.super_pow_therapist_collection
    cur = super_pow_therapist_collection.count_documents({})

    all_therapist=list(super_pow_therapist_collection.find({}, {"_id": 0}))
    
    return all_therapist



def get_initial_score(all_therapist, language, ethnicity, lgbt):
    '''
        loop through the therapist and score them based on language, ethnicity and lgbtq choice
    '''
    initial_score = []
    comments = []
    therapist_language = []
    
    
    for item in all_therapist:
        score = 0
        comment = []
        if language.lower() in item['language'].lower():
            
            score +=2
            comment.append("Matched by language")
        else:
            pass


        if ethnicity.lower() == item['Ethnicity'].lower():
            score+=1
            comment.append("Matched by Ethnicity")


        try:
            if lgbt.lower() == "yes" and ("lgbtq" in item['bio'].lower() or "lgbt" in item.get('HoW I WORK').lower() or "lgbt" in item['What I CAN HELP WITH'].lower()):
                score +=1
                comment.append("Matched by LGBTQ choice")

            elif lgbt.lower() == "no":
                score +=0
            elif lgbt.lower() == "maybe" and ("lgbtq" in item['bio'].lower() or "lgbt" in item.get('HoW I WORK').lower() or "lgbt" in item['What I CAN HELP WITH'].lower()):
                score +=0.5
                
        except:
            pass
        therapist_language.append(item['language'])
        initial_score.append(score)
        comments.append(comment)
    
    return initial_score, comments, therapist_language


def get_additional_score(all_therapist, user_symptoms):
    '''
        loop through the the therapist and score based on the word vector similarity 
    '''
    other_score = []
    therapist_name = []
    symptoms = []

    for item in all_therapist:

        user_symptoms = user_symptoms.lower()
        user_symptoms_df = pd.Series(user_symptoms)
        
        try:
            therapist_symptoms = item['What I CAN HELP WITH']
            therapist_df = pd.Series(therapist_symptoms)
        except:
            therapist_df = pd.Series("nil")

        tfidf_vec=TfidfVectorizer(stop_words='english')
        tfidf_vec.fit(therapist_df)


        therapist_tfidf=tfidf_vec.transform(therapist_df)
        user_symptoms_tfidf=tfidf_vec.transform(user_symptoms_df)


        similarity_scores = therapist_tfidf.dot(user_symptoms_tfidf[0].toarray().T)[0][0]

        other_score.append(similarity_scores)
        therapist_name.append(item['name'])


        user_symptoms_tokens = word_tokenize(user_symptoms)
        user_symptoms_tokens = [word for word in user_symptoms_tokens if not word in stopwords.words()]
        user_symptoms_tokens = [word for word in user_symptoms_tokens if not word in string.punctuation]

        symptom = []
        for word in user_symptoms_tokens:
            if word in therapist_symptoms.lower():
                symptom.append(word)

        matching_dict = {"matching_symptoms": symptom}
        symptoms.append(matching_dict)
    
    
    return other_score, therapist_name, symptoms


def merge_scores(initial_score, other_score, therapist_name, symptoms, comments, therapist_language):
    complete_score = [initial_score[i] + other_score[i] for i in range(len(initial_score))] 

    df = pd.DataFrame()

    df['therapist_name'] = therapist_name
    df['therapist_language'] = therapist_language
    df['score'] = complete_score
    df['matching_comments'] = comments
    df['matching_symptoms'] = symptoms
    
    df = df.sort_values(by=['score'], ascending=False) 
    
    return df

def get_recommendations(language, ethnicity, lgbt, user_symptoms):
    all_therapist = get_therapist_from_db()
    
    initial_score, comments, therapist_language = get_initial_score(all_therapist, language, ethnicity, lgbt)
    
    other_score, therapist_name, symptoms = get_additional_score(all_therapist, user_symptoms)
    
    df = merge_scores(initial_score, other_score, therapist_name, symptoms, comments, therapist_language)
    
    return df.to_dict('records')[:3]

