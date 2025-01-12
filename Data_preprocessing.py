import pandas as pd

df = pd.read_csv('interpark_reviews.csv')

print(df.columns)
print(df['star_rating'])