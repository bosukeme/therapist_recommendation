from pymongo import MongoClient
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
import string
from decouple import config as env_config

MONGO_URL =  env_config('MONGO_URL')

client= MongoClient(MONGO_URL, connect=False)
db = client.bacp_counselling


def get_therapist_from_db():
    '''
        Query the DB and return all the therapist saved there
    '''
    trying_collection = db.trying_collection

    all_therapist = list(trying_collection.find({}))    

    return all_therapist



def get_initial_score(all_therapist, language, ethnicity, lgbt, gender):
    '''
        loop through the therapists and score them based on language, ethnicity and lgbtq choice
    '''
    initial_score = []
    comments = []
    therapist_language_list = []
    therapist_ids = []
    language_scores_list = []
    ethnicity_scores_list = []
    
    
    for item in all_therapist:
        score = 0
        comment = []
        therapist_id = str(item['_id'])

        ###### score on Gender selection
        if gender.lower() == item['Gender'].lower():
            score+=1
            comment.append("Matched by Gender Choice")

            
        ###### score by age selection
        try:
            therapist_age_datetime =  item['Date of Birth']
            therapist_year = datetime.strptime(therapist_age_datetime, '%d/%M/%Y').year
            current_year = datetime.now().year

            therapist_age = current_year - therapist_year
        except:
            therapist_age = "NA"
        
        
        ##### score on language selection
        user_language = language.lower()  
        therapist_language = item['Languages You Speak (separate by comma)'].lower()
        
        user_language_df = pd.Series(user_language)
        therapist_language_df = pd.Series(therapist_language)
        
        tfidf_vec=TfidfVectorizer(stop_words='english')
        tfidf_vec.fit(therapist_language_df)

        
        therapist_language_tfidf = tfidf_vec.transform(therapist_language_df)
        user_language_tfidf = tfidf_vec.transform(user_language_df)
        

        language_scores = therapist_language_tfidf.dot(user_language_tfidf[0].toarray().T)[0][0]
        language_scores_list.append(language_scores)
        
        if language_scores > 0.5:
            comment.append("Matched by language")
        else:
            pass
        

        ##### score by ethnicity selection
        user_ethnicity = ethnicity.lower()  
        therapist_ethnicity = item['Ethnicity'].lower()
    
        user_ethnicity_df = pd.Series(user_ethnicity)
        therapist_ethnicity_df = pd.Series(therapist_ethnicity)
        
        tfidf_vec=TfidfVectorizer(stop_words='english')
        tfidf_vec.fit(therapist_ethnicity_df)

        
        therapist_ethnicity_tfidf = tfidf_vec.transform(therapist_ethnicity_df)
        user_ethnicity_tfidf = tfidf_vec.transform(user_ethnicity_df)
        
        
        ethnicity_scores = therapist_ethnicity_tfidf.dot(user_ethnicity_tfidf[0].toarray().T)[0][0]
        ethnicity_scores_list.append(ethnicity_scores)
        
        if ethnicity_scores > 0.5:
            comment.append("Matched by Ethnicity")
        else:
            pass


        try:
            if lgbt.lower() == item['Are you a member of the LGBT community?'].lower():
                score+=1
                comment.append("Matched by LGBTQ choice")
            
            elif lgbt.lower() == "doesn't matter":
                score+=0.5
                
            else:
                pass

                
        except:
            pass

        therapist_language_list.append(item['Languages You Speak (separate by comma)'])
        initial_score.append(score)
        comments.append(comment)
        therapist_ids.append(therapist_id)
    
    return initial_score, comments, therapist_language_list, therapist_ids, language_scores_list, ethnicity_scores_list


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
            therapist_symptoms = str(item['What I can help with'])
            therapist_df = pd.Series(therapist_symptoms)
        except:
            therapist_df = pd.Series("nil")

        tfidf_vec=TfidfVectorizer(stop_words='english')
        tfidf_vec.fit(therapist_df)


        therapist_tfidf=tfidf_vec.transform(therapist_df)
        user_symptoms_tfidf=tfidf_vec.transform(user_symptoms_df)


        similarity_scores = therapist_tfidf.dot(user_symptoms_tfidf[0].toarray().T)[0][0]

        other_score.append(similarity_scores)
        therapist_name.append(item['Name'])


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


def merge_scores(therapist_ids, initial_score, other_score, therapist_name, symptoms, comments, therapist_language, language_scores_list, ethnicity_scores_list):
    complete_score_1 = [initial_score[i] + other_score[i] for i in range(len(initial_score))] 
    
    complete_score_2 = [language_scores_list[i] + ethnicity_scores_list[i] for i in range(len(language_scores_list))]
    
    total_score = [complete_score_1[i] + complete_score_2[i] for i in range(len(complete_score_1))]

    df = pd.DataFrame()
    
    df['therapist_id'] = therapist_ids
    df['therapist_name'] = therapist_name
    df['therapist_language'] = therapist_language
    df['score'] = total_score
    df['matching_comments'] = comments
    df['matching_symptoms'] = symptoms
    
    df = df.sort_values(by=['score'], ascending=False) 
    
    return df


def get_recommendations(language, ethnicity, lgbt, user_symptoms, gender):
    
    all_therapist = get_therapist_from_db()
    
    initial_score, comments, therapist_language, therapist_ids, language_scores_list, ethnicity_scores_list = get_initial_score(all_therapist, language, ethnicity, lgbt, gender)
    
    other_score, therapist_name, symptoms = get_additional_score(all_therapist, user_symptoms)
    
    df = merge_scores(therapist_ids, initial_score, other_score, therapist_name, symptoms, comments, therapist_language, language_scores_list, ethnicity_scores_list)
    
    return df.to_dict('records')[:3]

