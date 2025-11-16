Syllabus Bender:
  A project for students/users to store their syllabusses of their classes of the cemester and summarize the lecture content with the help of AI, and get help scheduling the studying plan for their clases, etc.





How to run:
*select branch main
*download the repository
*(Assuming you have ptyhon installed) install the rqeuirements.txt content with pip:
  pip install -r ./requirements.txt
*Open a new terminal page in the downloaded folder
*define an environment variable for API key:
  $env:GEMINI_API_KEY='AIzaSyAelduUiVY_8cGfcVUL4RX5Yhr0o2wk9rQ' (you can use your own API key too, get it from google ai studio)
*execute the project with command:
  flask run
*ctrl+click the website link
*you have to register to use the services.
*ENJOY OUR PROJECT!!!!




## Inspiration
While in school, if we were to e-mail a tutor or check what time the office hours ours were, we had to look up every syllabus of our classes seperately. So, we thought what if these syllabusses handed at the beginning of the cemesters we're organizes and tidy? We thought of an app gathering these syllabusses and summarizing them with the help of AI. So, we created Syllabus Bender! 
## What it does
In this website, users register and upload the syllabusses of their lectures they take this cemester. The system reads those files and summarizes them, also recommends some content in the internet to study that lecture. This way, users have a way to gather their lecture information together for each cemester in their schools.
## How we built it
We used flask for backend and html with jinja for the web app.
## Challenges we ran into
Some version control problems gave us a very hard time. We had to go back a couple of commits to continiue.
## Accomplishments that we're proud of
The system succesfully takes the syllabus files as input and stores the summaries of the lectures, stores them for each user and creates a simple schedule in .ics file format.
## What we learned
Database design, prompt engineering, flask, web development, version control
## What's next for Syllabus Bender
The user can enter the duration of the cemester he is in and the system divides the lecture material through the weeks of the cemester and create a calendar to study to that lecture.

