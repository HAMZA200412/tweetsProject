from flask import Flask, render_template, request, session
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
from transformers import pipeline


chrome_driver_version = "129.0.6668.58"

# Replace with your Twitter credentials
username = "__________"
password = "_______"

app = Flask(__name__)

app.secret_key = '_____'

sent_pipeline = pipeline("sentiment-analysis")

def perform_sentiment_analysis(texts):
    sentiments = sent_pipeline(texts)

    results = []
    for sentiment in sentiments:
        label = sentiment['label']
        score = sentiment['score']

        if label == "POSITIVE":
            results.append(f"Positive ☺️ (confidence: {score:.2f})")
        elif label == "NEGATIVE":
            results.append(f"Negative 😵 (confidence: {score:.2f})")
        else:
            results.append(f"Neutral 😑 (confidence: {score:.2f})")

    return results

# Function to log in to Twitter
def twitter_operations(username, password,topic,iterations):
    # Setup Selenium WebDriver with ChromeDriverManager
    driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_driver_version).install()))

    login_url = "https://twitter.com/login"
    driver.get(login_url)

    try:
        # Wait until the username field is present
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, "text"))
        )

        # Enter the username
        username_input = driver.find_element(By.NAME, "text")
        username_input.send_keys(username)
        # Click the Next button
        next_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//span[contains(text(),"Suivant")]/ancestor::button'))
        )
        next_button.click()

        # Wait for the password field to appear
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )

        # Enter the password
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys(password)
        # Click the Login button
        login_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//span[contains(text(),"Se connecter")]/ancestor::button[@data-testid="LoginForm_Login_Button"]'))
        )
        login_button.click()

        # Wait until the home page loads
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="primaryColumn"]'))
        )
    except Exception as e:
        print(f"Error during login: {e}")


    # Create a search URL
    search_url = f"https://twitter.com/search?q={topic}&src=typed_query"
    driver.get(search_url)
    tweet_data = []
    try:
        # Wait until at least one tweet is present
        WebDriverWait(driver, 90).until(
            EC.presence_of_element_located((By.XPATH, '//article[@data-testid="tweet"]'))
        )

        for _ in range(iterations):
            # Fetch tweets
            tweets = driver.find_elements(By.XPATH, '//article[@data-testid="tweet"]')

            for tweet in tweets:
                try:
                    # Extract the tweet text
                    tweet_text_element = tweet.find_element(By.XPATH, './/div[@data-testid="tweetText"]')
                    tweet_text = tweet_text_element.text

                    # Extract the tweet time
                    tweet_time = tweet.find_element(By.TAG_NAME, 'time').get_attribute('datetime')

                    #Extract username
                    username_element = tweet.find_element(By.XPATH, './/div[@class="css-175oi2r r-1wbh5a2 r-dnmrzs"]//a[@role="link"]//span[@class="css-1jxf684 r-dnmrzs r-1udh08x r-3s2u2q r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3"]')
                    username = username_element.text

                    # Extract the number of comments
                    comments_count_element = tweet.find_element(By.XPATH, './/button[@data-testid="reply"]//span[@data-testid="app-text-transition-container"]//span[@class="css-1jxf684 r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3"]')
                    comments_count = comments_count_element.text

                    # Extract the number of repostes
                    repost_count_element = tweet.find_element(By.XPATH, './/button[@data-testid="retweet"]//span[@data-testid="app-text-transition-container"]//span[@class="css-1jxf684 r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3"]')
                    repost_count = repost_count_element.text

                    # Extract the number of repostes
                    like_count_element = tweet.find_element(By.XPATH, './/button[@data-testid="like"]//span[@data-testid="app-text-transition-container"]//span[@class="css-1jxf684 r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3"]')
                    like_count = like_count_element.text


                    tweet_data.append({
                        'user_name':username,
                        'text': tweet_text,
                        'time': tweet_time,
                        'repostes': repost_count,
                        'comments':comments_count,
                        'likes':like_count
                    })

                    time.sleep(1)

                except NoSuchElementException as e:
                    print(f"Error extracting tweet data: {e}")

            # Scroll down to load more tweets
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait for new tweets to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//article[@data-testid="tweet"]'))
            )

    except TimeoutException:
        print("No more tweets found or loading took too long.")
    except Exception as e:
        print(f"Error loading tweets: {e}")

    driver.quit()

    return tweet_data

@app.route("/")
def index():
    return render_template("a.html")


@app.route("/scrap", methods=["POST"])
def scrap():
    topic = request.form['topic']
    iterations = int(request.form['iterations'])  # Convert to integer
    tweets = twitter_operations(username, password, topic, iterations)

    # Create a DataFrame
    df = pd.DataFrame(tweets, columns=['user_name', 'time', 'text', 'comments', 'repostes', 'likes'])

    ## Store the DataFrame in session as JSON
    session['tweets'] = df.to_json(orient='records')

    # Convert DataFrame to HTML
    table_html = df.to_html(classes='table table-striped', index=False, escape=False)

    return render_template('results.html', table_html=table_html)

@app.route("/sentiment_analysis", methods=["POST"])
def sentiment_analysis():
    # Get the tweet data from the session
    tweets_json = session.get('tweets')
    if not tweets_json:
        return "No tweet data found.", 400

    df = pd.read_json(tweets_json)

    # Perform sentiment analysis
    results = perform_sentiment_analysis(df['text'].tolist())
    df['sentiment'] = results

    # Convert updated DataFrame to HTML with sentiment
    table_html = df.to_html(classes='table table-striped', index=False, escape=False)
    return render_template('results.html', table_html=table_html)


if __name__ == "__main__":
        app.run(host="0.0.0.0", debug=True)
