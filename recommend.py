# Basic recommendation engine, written as an exercise in learning recommender
# algorithms. It takes a CSV file of reviews with the format specified in the 
# code, the maximum recommendations, and a list of businesses for which the
# user would like recomendations. The recommendations are calculated by 
# Pearson's corrolation coefficient over common reviewers of pairs of 
# businesses. Note that if a buiness has multiple locations, a different list 
# is printed per location.
#
#   Copyright (C) 2016   Ezra Erb
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 3 as published
#   by the Free Software Foundation.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#   I'd appreciate a note if you find this program useful or make
#   updates. Please contact me through LinkedIn or github (my profile also has
#   a link to the code depository)
#
import sys
import math
from csv import DictReader
from collections import namedtuple
from operator import attrgetter
from collections import defaultdict

# The file records are the join between the user, the business, and the review. 
# Want to split the record into three, one for each part. The first two are 
# stored as classes. If no record exists for the given ID, just insert it 
# into the appropriate data store, otherwise verify the new record matches. The
# review then gets added to both records, indexed under the OTHER ID. 
class ReviewInfo():
      def __init__(self, name, review_avg):
          self._name = name
          self._reviews = {}
          self._review_avg = review_avg

      def __repr__(self):
          return self._name + " _reviews:" + str(self._reviews) + " _review_avg:" + str(self._review_avg)

      def __str__(self):
          return self.__repr__()

      def summary_info(self):
          # Returns all data except the reviews as a tuple
          return (self._name, self._review_avg)

# Load data and return two dictionaries, one indexing reviews by business
# the other by reviewer. Need both
def load_data(filename):
    user_data = {}
    business_data = {}
    with open(filename, 'rt') as fin:
         cin = DictReader(fin, fieldnames = ['user_id', 'business_id', 'date', 'review_id', 'stars', 'usefulvotes_review', 'user_name', 'categories', 'biz_name', 'latitude', 'longitude', 'business_avg', 'business_review_count', 'user_avg', 'user_review_count'])
         # Verify that the wanted columns exist, in the correct places
         first_row = next(cin)
         if (first_row["user_id"] != 'user_id') or \
            (first_row["business_id"] != 'business_id') or \
            (first_row["stars"] != 'stars') or \
            (first_row["user_name"] != 'user_name') or \
            (first_row["biz_name"] != 'biz_name') or \
            (first_row["business_avg"] != 'business_avg') or \
            (first_row["user_avg"] != 'user_avg'):
            print "Error in file " + filename + " Expected columns: user_id,business_id,date,review_id,stars,usefulvotes_review,user_name,categories,biz_name,latitude,longitude,business_avg,business_review_count,user_avg,user_review_count"
         else:
             for row in cin:
                 # Fields read as strings, convert for convenience
                 user_avg = float(row["user_avg"])
                 business_avg = float(row["business_avg"])
                 stars = float(row["stars"])
                 insert_user = False
                 if row["user_id"] in user_data:
                    user = user_data[row["user_id"]].summary_info()
                    if (row["user_name"] != user[0]) or (user_avg != user[1]):
                       print "Record skipped. User data mismatch for user_id " + row["user_id"] + " first: " + str(user) + " Now: " + row["user_name"] + " " + str(user_avg)
                       continue
                 # If not present can't insert yet, need to test business first
                 else:
                    insert_user = True
                 if row["business_id"] in business_data:
                    business = business_data[row["business_id"]].summary_info()
                    if (row["biz_name"] != business[0]) or (business_avg != business[1]):
                       print "Record skipped. Business data mismatch for business_id " + row["business_id"] + " first: " + str(business) + " Now: " + row["biz_name"] + " " + str(business_avg)
                       continue
                 else: 
                    business_data[row["business_id"]] = ReviewInfo(row["biz_name"], business_avg)
                 if insert_user:
                    user_data[row["user_id"]] = ReviewInfo(row["user_name"], user_avg)
                 # Insert the review in both. This assumes only the last review
                 # for a given user is wanted (and implictly implies the rows
                 # in the file increase by date for a given user)
                 user_data[row["user_id"]]._reviews[row["business_id"]] = stars
                 business_data[row["business_id"]]._reviews[row["user_id"]] = stars

    return (user_data, business_data)


# Helper function for the filter function below. Given a data structure of
# review data and a set of what to delete from it, do so and recalculate
# review averages
def filter_one_data(review_data, drop_data, drop_reviews):
   for entity in review_data.keys():
       if entity in drop_data:
          del review_data[entity]
       else:
          review_total = 0.0
          for review in review_data[entity]._reviews.keys():
              if review in drop_reviews:
                 del review_data[entity]._reviews[review]
              else:
                  # Since the number of reviews changed, need to recompute the
                  # average which requires the total of kept reviews
                  review_total += review_data[entity]._reviews[review]

          # If the entity has no reviews at this point, all of their reviewed
          # entities will ultimately be dropped. Drop this entity too
          if not review_data[entity]._reviews:
             del review_data[entity]
          else:
             review_data[entity]._review_avg = review_total / len(review_data[entity]._reviews)
   return review_data

# Given user reviews and business reviews, extract only the reviews by users
# above a certain amount of businesses with reviews above a certain amount.
# This routine shrinks a data set to a tractable size while biasing it toward
# the most popular reviewers and businesses
def filter_data(user_data, business_data, min_user_review_count, 
                min_business_review_count):
   # Can't test while filtering is in progress, because the number of 
   # user/business reviews changes. Find the list of what to delete up front and
   # then remove as appropriate
   drop_users = set()
   drop_businesses = set()
   for user in user_data.keys():
       if len(user_data[user]._reviews) < min_user_review_count:
          drop_users.add(user)
   for business in business_data.keys():
       if len(business_data[business]._reviews) < min_business_review_count:
          drop_businesses.add(business)

   # Now remove any users and businesses in those sets. 
   user_data=filter_one_data(user_data, drop_users, drop_businesses)
   business_data=filter_one_data(business_data, drop_businesses, drop_users)

   return (user_data, business_data)   

def normalize_reviews(user_data, business_data):
    # User reviews have an inherent bias. Some like all businesss and some
    # hate nearly all of them. To get business reviews comparable across users
    # need to normalize them as the difference between a given review and the
    # average for that user over all reviews. This routine does it for the
    # business data
    for business in business_data.keys():
        review_total = 0.0
        for user in business_data[business]._reviews.keys():
            if not user in user_data:
               print "ERROR: Inconsistent data. Business review for user " + user + " not in user data"
               del business_data[business]._reviews[user]
            else:
                business_data[business]._reviews[user] -= user_data[user]._review_avg            
                review_total += business_data[business]._reviews[user]
        if not business_data[business]._reviews:
           # All reviews have been dropped, drop the business
           del business_data[business]
        else:
           business_data[business]._review_avg = review_total / len(business_data[business]._reviews)
    return business_data

def pearsons_coefficient(first_reviews, second_reviews, regularize_coefficient):
    # This method calculates pearson's corrolation coefficient by the classic
    # variance formula. This multi-stage calculation was chosen due to its
    # relative computational accuracy. The size of the input should be small
    # on average. The coefficient tends to overestimate for small data sets, so
    # it is then scaled to compensate by the regularizer ratio

    if (len(first_reviews) != len(second_reviews)):
       print "Pearsons Coefficient failed, input data are differnt sizes " + str(len(first_reviews)) + " " + str(len(second_reviews))
       return 0.0

    data_size = len(first_reviews)

    # Need at least two data points per sample or the calculation fails 
    # (no variance!)
    if (data_size < 2):
       return 0.0

    first_mean = 0.0
    for first_data in first_reviews:
        first_mean += first_data
    first_mean /= data_size

    second_mean = 0.0
    for second_data in second_reviews:
        second_mean += second_data
    second_mean /= data_size

    first_variance = 0.0
    for first_data in first_reviews:
        first_variance += pow(first_data - first_mean, 2)

    second_variance = 0.0
    for second_data in second_reviews:
        second_variance += pow(second_data - second_mean, 2)

    combined_variance = math.sqrt(first_variance * second_variance)
    # No variance equals no ratio
    if (combined_variance == 0.0):
       return 0.0

    covariance = 0.0
    for index in range(data_size):
        covariance += ((first_reviews[index] - first_mean) * (second_reviews[index] - second_mean))
    result = covariance / combined_variance

    # Now adjust the ratio to account for overestimation bias with small samples
    result = (result * data_size) / (data_size + regularize_coefficient)
    return result

def find_similarity_data(user_data, business_data):
    # Calculating similarity of businesss requires knowing which users reviewed
    # pairs of businesss. This can be calculated very efficiently using sets.
    # That in turn requires knowing the reviewers of each business as a set. 
    # The data will be needed often enough that its most efficient to calculate
    # it up front instead of using memoization
    reviewer_sets = {}
    for business in business_data.keys():
        reviewer_sets[business] = set(business_data[business]._reviews.keys())

    # Need to compare every business with every other business. This is 
    # most efficiently done with a double loop. 
    SimilarityData = namedtuple('SimilarityData', 'id name review_avg similarity common_count')

    # Ideally, want to look up business similarities by name. Unfortunately, 
    # businesss with different locations can have the same name. This code 
    # handles it with a double-level dictionary, one for names and a second for
    # IDs for matching names
    # See also: http://stackoverflow.com/questions/19189274/defaultdict-of-defaultdict-nested
    recommend_result = defaultdict(lambda: defaultdict(list))
    business_list = business_data.keys()
    for first_index in range(len(business_list) - 1):
        for second_index in range(first_index + 1, len(business_list)):
            first_business = business_list[first_index]
            second_business = business_list[second_index]
            overlap = reviewer_sets[first_business] & reviewer_sets[second_business]
            # Need at least two reviewers for a valid similarity rating
            if len(overlap) < 2:
               continue
            # Reviews must be in the same order for both
            first_reviews = []
            second_reviews = []
            for reviewer in overlap:
                first_reviews.append(business_data[first_business]._reviews[reviewer])
                second_reviews.append(business_data[second_business]._reviews[reviewer])
            similarity = pearsons_coefficient(first_reviews, second_reviews, 3)
            # If similarity is negative, the business is NOT recommended
            if (similarity < 0):
               continue
            # Insert results for both businesses. See above for the complexity
            # of this index
            first_business_name = business_data[first_business]._name
            second_business_name = business_data[second_business]._name
            recommend_result[first_business_name][first_business].append(SimilarityData(second_business, second_business_name, business_data[second_business]._review_avg, similarity, len(overlap)))
            recommend_result[second_business_name][second_business].append(SimilarityData(first_business, first_business_name, business_data[first_business]._review_avg, similarity, len(overlap)))

    # Iterate through the results and sort them by similarity
    for business_name in recommend_result:
        for business in recommend_result[business_name]:
            recommend_result[business_name][business].sort(key=attrgetter('similarity'), reverse=True)
    return recommend_result

if len (sys.argv) < 4:
   print "Usage [Data file] [maximum recommendations] [business for recommendations] (additional businesss)"
else:
   (user_data, business_data) = load_data(sys.argv[1])
   (user_data, business_data) = filter_data(user_data, business_data, 60, 150)
   business_data = normalize_reviews(user_data, business_data)
   recommend_result = find_similarity_data(user_data, business_data)

   # Iterate though the arguments and print the recommendations
   recommend_limit = int(sys.argv[2])
   for arg_index in range(3, len(sys.argv)):
       business = sys.argv[arg_index]
       if not sys.argv[arg_index] in recommend_result:
          print "No recommendations available for those who like " + business
       else:
          print "Recommendations for those who like " + business + ":"
          if len(recommend_result[business]) > 1:
             print "Multiple businesss by that name found"
          for business_id in recommend_result[business]:
              print "  " + business_id + ":"
              business_limit = len(recommend_result[business][business_id])
              if (recommend_limit > 0) and (recommend_limit < business_limit):
                 business_limit = recommend_limit
              for business_index in range(business_limit):
                  business_data = recommend_result[business][business_id][business_index]
                  print "    " + business_data.name + ": review avg: " + \
                  str(business_data.review_avg) + " similarity rating: " + \
                  str(business_data.similarity) + " common reviewers: " + \
                  str(business_data.common_count)

