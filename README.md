# CS410 Final Project Code Submission

## Overview

This project is a UIUC ECE question-answering and feedback analysis application. Users can upload an ECE course JSON file, ask natural-language questions about the course records, receive an AI-generated answer, provide thumbs-up/thumbs-down feedback, and optionally submit written department feedback.

The app uses uploaded course records to generate answers, displays the records used for reference, downweights unhelpful records based on user feedback, and saves department feedback with sentiment results to an Excel file.

## Setup Instructions

### 1. Install dependencies

Open PowerShell in the project folder and run:

```powershell
python -m pip install -r requirements.txt
```

### 2. Create your own OpenRouter API key

This application requires an OpenRouter API key.

Go to:

https://openrouter.ai/

Create an account, generate your own API key, and set it as an environment variable in PowerShell:

```powershell
$env:OPENROUTER_API_KEY="your_api_key_here"
```

Do not paste your API key directly into the source code. Do not commit your API key to GitHub.

### 3. Train/load the sentiment analysis model

Before running the main app, run the sentiment training script:

```powershell
python train_sentiment_v2.py
```

This step trains or loads the sentiment analysis model used to classify department feedback.

### 4. Run the app

After the sentiment model step finishes, run:

```powershell
python app_v2.py
```

The app should open locally in your browser.

## Fast Setup Commands for PowerShell

Copy and paste these commands in order:

```powershell
python -m pip install -r requirements.txt
$env:OPENROUTER_API_KEY="your_api_key_here"
python train_sentiment_v2.py
python app_v2.py
```

Replace `your_api_key_here` with your own OpenRouter API key.

## How to Use the App

### 1. Upload the ECE courses JSON file

Download the ECE courses JSON file provided for the project.

Once the app is running, drag the ECE courses JSON file into the file upload box.

The app uses this JSON file as the source of course and department information.

### 2. Ask a question

Type a question into the question box and click **Ask**.

Example questions:

```text
Which courses are related to signal processing?
```

```text
I am very interested in circuit design and architecture. Which classes should I take?
```

```text
What are some introductory level courses that I should take?
```

After clicking **Ask**, the response may take 30-60 seconds to appear. Please wait for the answer to load. Since we are using a free API, it may take longer than expected.

### 3. Review the answer and records

After the answer is generated, the app displays the response along with the relevant records used for reference.

The records section is included for demo purposes so that you can see what information the system used to help generate the answer.

### 4. Provide thumbs-up or thumbs-down feedback

After receiving an answer, scroll down past the records section and click either:

- Thumbs up, if the answer was helpful
- Thumbs down, if the answer was not helpful

This feedback affects the weights of the records used by the system.

In this implementation, the weighting system only downweights records after negative feedback. These downweight values are saved in:

```text
faq_state.json
```

This file can be accessed in the project folder and represents part of the app’s backend state.

### 5. Submit department feedback

After the thumbs-up/thumbs-down section, scroll further down to write feedback for the ECE department.
Example feedback to submit:

```text
I hate how fast ECE 210 is paced
```

```text
I think that the ECE 313 professors do a great job of teaching the course
```

```text
Can we please restock the vending machines on the first floor?
```

When a user submits written department feedback, the app saves both the feedback and its predicted sentiment into an Excel file.

This Excel file can be accessed in the project folder after feedback is submitted.

The sentiment analysis helps classify student feedback so that the department can better understand areas of strength and areas that may need improvement.

## Main Features

- Uploads and reads ECE course JSON data
- Answers natural-language questions using relevant course records
- Uses OpenRouter API for AI-generated responses
- Displays relevant records for transparency
- Allows users to rate answers with thumbs-up or thumbs-down feedback
- Downweights records after negative feedback
- Saves downweight state to `faq_state.json`
- Collects written department feedback
- Runs sentiment analysis on written department feedback
- Saves department feedback and predicted sentiment to an Excel file

## Important Notes

- Each user must create their own OpenRouter API key.
- The API key must be set locally as an environment variable.
- The API key should never be committed to GitHub.
- The sentiment model script must be run before starting the app.
- The ECE courses JSON file must be uploaded through the file upload box before asking questions.
- AI responses may take 30-60 seconds to appear after clicking **Ask**.
- Users should scroll below the records section after receiving a response to provide thumbs-up/thumbs-down feedback.
- In this implementation, record weighting only applies downweights after negative feedback.
- Written department feedback is saved with sentiment results in an Excel file.

## File Outputs

The app may create or update output files during use, including:

- `faq_state.json`, which stores record downweight information after negative answer feedback
- An Excel file containing written department feedback and predicted sentiment results

These files represent backend outputs generated by the application and can be accessed directly from the project folder.

## Security Reminder

Do not include API keys in the README, source code, or any committed files.

If an API key was previously committed or shared, it should be revoked and replaced with a new key.
