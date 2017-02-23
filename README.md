# CanvasSBG
An app to pull data from Instructure's Learning Mastery Gradebook and auto-send messages to students.

We are attempting to grade with a standards-based mindset at our school and found that the Learning Mastery Gradebook from Instructure didn't entirely meet our needs. Primarily, we are wanting a means of nesting learning targets (called "outcomes" in Canvas) under power standards (called "outcome groups" in Canvas), and providing average scores for students on these power standards based on their learning target scores. Currently, Canvas only provides a means of reporting on learning targets using a few different calculation methods.

This application pulls data from the Learning Mastery Gradebook and retructures it to create average outcome group scores. These scores are inserted into a templated message and sent to each student in the course via the Canvas inbox. 

There are a few assumptions made in order to run the program without exceptions at this point.
    The user already has generated an access token in their Canvas account.
    The user knows the ID for their course, found in the URL for their course homepage --> yourdomain.intructure.com/courses/YOUR_ID
    The user knows the account ID # for their institutional account. This may have to be obtained from the site admin.
    The program looks for a config file within the same directory. There is functionality included to generate one.
    The program also looks for the messagetemplate.txt file in the same directory when generating student messages.
    
The GUI is built on TKinter, which I am learning for the first time. I am very interested in collaborating with someone who knows Tkinter well to make it nice and pretty (a Tkinterer?)

Additionally, I'm interested in optimizing code wherever possible!
