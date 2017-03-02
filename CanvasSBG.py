# -*- coding: utf-8 -*-
"""
Created on Wed Feb 15 08:56:04 2017

@author: brueckert
"""

import tkinter as tk
from tkinter import messagebox
from statistics import mean
import requests, pickle, json, csv

class SBGApp(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand = True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        self.app_data = {'baseURL':     tk.StringVar(),
                         'apiURL':      tk.StringVar(),
                         'account':     tk.StringVar(),
                         'token':       tk.StringVar(),
                         'courseTitle': tk.StringVar(),
                         'courseID':    tk.StringVar(),
                         'rawGradeData':[],
                         'courseUsers': [],
                         'fullGBook':   [] 
        }        
        
        self.preview = ''
        self.frames = {}
        
        for F in (FirstPage, ConfigsPage, PageTwo, PageThree, PageFour, PageFive, StudentPreview):

            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        self.show_frame(FirstPage)

    def show_frame(self, page):
        frame = self.frames[page]
        frame.tkraise()
        
    
    def setConfigs(self):
        '''
        Sets self.app_data info via a user provided pickle file in same directory
        '''
        try:
            inFile = open('Configs.pkl', 'rb')
        except FileNotFoundError:
            messagebox.showinfo(title='Error', message='Configs.pkl not found please create Config file first.')
            self.show_frame(ConfigsPage)
        else:
            pickleData = []
            for i in range(4):
                pickleData.append(pickle.load(inFile))
            inFile.close()
            self.app_data['baseURL'].set(pickleData[0])
            self.app_data['apiURL'].set(pickleData[1])
            self.app_data['account'].set(pickleData[2])
            self.app_data['token'].set(pickleData[3])
        
            self.show_frame(PageTwo)
    
    def getCourseTitle(self, courseID):
        '''
        Sets the class instance variable to display course title
        '''
        r = requests.get(self.app_data['apiURL'].get() + 'courses/' + courseID,
                headers = {'Authorization': 'Bearer {}'.format(self.app_data['token'].get())})
        d = r.json()
        #print(json.dumps(d,sort_keys=True,indent=4))
        self.app_data['courseID'].set(courseID)
        self.app_data['courseTitle'].set(d['name'])
        #tk.messagebox.showinfo(title='Course Set', message='Course has been set to ' + self.app_data['courseTitle'].get())
        self.show_frame(PageThree)
    
    def buildGradebook(self, courseID):    
        '''
        Gets user data and outcome results from course and stores them in app_data
        Builds master dict of users, names, loginIDs, outcome group titles and average scores
        '''
        
        #Part 1: Gathers outcome rollup data for every student in course
        payload = {'include':['outcome_groups']}
        r = requests.get(self.app_data['apiURL'].get() + 'courses/' + courseID + '/outcome_rollups',
                headers = {'Authorization': 'Bearer {}'.format(self.app_data['token'].get())}, params=payload)
        outData = r.json()
        while 'next' in r.links:
            r = requests.get(r.links["next"]["url"],
                headers = {'Authorization': 'Bearer {}'.format(self.app_data['token'].get())}, params=payload)
            rtemp = r.json()
            outData['rollups'] += rtemp['rollups']
        #print(json.dumps(outData,sort_keys=True,indent=4))
        self.app_data['rawGradeData'] = outData
    
    
        #Part 2: Gathers list of student ids and usernames
        payload = {'enrollment_type':'student'}
        r = requests.get(self.app_data['apiURL'].get() + '/courses/' + courseID + '/users',
                headers = {'Authorization': 'Bearer {}'.format(self.app_data['token'].get())}, params=payload)
        d = r.json()
        while 'next' in r.links:
            r = requests.get(r.links["next"]["url"],
                headers = {'Authorization': 'Bearer {}'.format(self.app_data['token'].get())}, params=payload)
            rtemp = r.json()
            d += rtemp
        #print(json.dumps(d,sort_keys=True,indent=4))
        keepMe = []
        for i in d:
            temp = {}
            temp['id'] = i['id']
            temp['name'] = i['name']
            temp['login_id'] = i['login_id']
            keepMe.append(temp)
        self.app_data['courseUsers'] = keepMe
        
        
        #Part 3: Gets outcome groups in course with outcome ids
        outcomesByGroup = []
        for i in self.app_data['rawGradeData']['linked']['outcome_groups']:
            tempD = {}
            tempD['title'] = i['title']
            groupURL = self.app_data['baseURL'].get() + i['outcomes_url']
            r = requests.get(groupURL, 
                    headers = {'Authorization': 'Bearer {}'.format(self.app_data['token'].get())})
            d = r.json()
            while 'next' in r.links:
                r = requests.get(r.links["next"]["url"],
                    headers = {'Authorization': 'Bearer {}'.format(self.app_data['token'].get())})
                rtemp = r.json()
                d += rtemp
            #print(json.dumps(d,sort_keys=True,indent=4))
            temp = []
            for j in d:
                try:
                    temp.append(j['outcome']['id'])
                except TypeError:
                    print('Skipping "NoneType"')
            tempD['outcomes'] = temp
            outcomesByGroup.append(tempD)
             
             
        #Part 4: Cross reference outcome ids in each group with rollup scores to generate
        #a new dict with group titles and group average scores for each student     
        users = self.app_data['courseUsers']
        for i in range(len(users)):
            users[i]['results'] = []
            for j in self.app_data['rawGradeData']['rollups']:
                if j['links']['user'] == str(users[i]['id']):
                    for k in range(len(outcomesByGroup)):
                        tempD = {}
                        tempD['title'] = outcomesByGroup[k]['title']
                        tempD['group_scores'] = []
                        for m in j['scores']:
                            for n in outcomesByGroup[k]['outcomes']:
                                if str(n) == m['links']['outcome']:
                                    tempD['group_scores'].append(m['score']) 
                        users[i]['results'].append(tempD)
        
        #removes any "results" items with no group scores
        for i in range(len(users)):
            users[i]['results'][:] = [x for x in users[i]['results'] if len(x['group_scores']) > 0]
                     
        #create new key in results titled "mean", which is average of group rollup scores
        for i in range(len(users)):
            for j in range(len(users[i]['results'])):
                users[i]['results'][j]['mean'] = mean(users[i]['results'][j]['group_scores'])
                
        self.app_data['fullGBook'] = users
        #messagebox.showinfo(title='Data Retrieved', message='Data from Canvas has been retrieved')
        self.show_frame(PageFour)


    def genPreviewMessage(self):
        '''
        Gets the first student in the master gradebook and generates their message, changing
        the data into a string. Template message must be in the same directory. Replaces
        <<name>> with student name and <<group_scores>> with string values of their outcome group scores
        '''
        t = open('messagetemplate.txt', 'r')
        template = t.read()
        t.close()

        groupScores = ''
        for i in self.app_data['fullGBook'][0]['results']:
            groupScores = groupScores + i['title'] + ': ' + str(i['mean']) + ' \n'
        
        template = template.replace('<<name>>', self.app_data['fullGBook'][0]['name'])
        template = template.replace('<<group_scores>>', groupScores)
        self.preview = template
        self.show_frame(StudentPreview)
        
    def genMessages(self):

        for i in self.app_data['fullGBook']:
            t = open('messagetemplate.txt', 'r')
            template = t.read()
            t.close()
            groupScores = ''
            for k in i['results']:
                groupScores = groupScores + k['title'] + ': ' + str(k['mean']) + ' \n'
            template = template.replace('<<name>>', i['name'])
            template = template.replace('<<group_scores>>', groupScores)
            
            payload = {'recipients':[str(i['id'])],
                      'subject':'Your Current Standard Scores',
                      'body':template,
            }
            
            r = requests.post(self.app_data['apiURL'].get() + '/conversations',
                    headers={'Authorization': 'Bearer {}'.format(self.app_data['token'].get())}, params=payload)
            d = r.json()
            print(json.dumps(d,sort_keys=True,indent=4))
            #print(template)
            self.show_frame(PageFive)
                        
                        
    def closeProgram(self):
        self.destroy()
    
    
    def genTeachReport(self):
        csvOut = []
        heads = ['name','login_ID',]
        for i in self.app_data['fullGBook'][0]['results']:
            heads.append(i['title'])
        for i in self.app_data['fullGBook']:
            toAdd = []
            toAdd.append(i['name'])
            toAdd.append(i['login_id'])
            for k in i['results']:
                for j in heads:
                    if j == k['title']:
                        toAdd.append(k['mean'])
            csvOut.append(toAdd)
        
        with open('StandardsReport.csv', 'w', newline='') as csvfile:
            writeOut = csv.writer(csvfile, delimiter=',',dialect='excel')
            writeOut.writerow(heads)
            for i in csvOut:
                writeOut.writerow(i)
        messagebox.showinfo(title='Export', message='Data exported to CSV')
        
        
class FirstPage(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)
        self.controller = controller
        b1 = tk.Button(self, text='Create Config File', command=lambda: self.controller.show_frame(ConfigsPage))
        b2 = tk.Button(self, text='Load Configs', command=lambda: self.controller.setConfigs())
        b1.grid(row=0,column=0)
        b2.grid(row=0,column=1)
        
class ConfigsPage(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)
        self.controller = controller
        lab1 = tk.Label(self, text='Root account URL: ')
        lab2 = tk.Label(self, text='API URL: ')
        lab3 = tk.Label(self, text='Account #')
        lab4 = tk.Label(self, text='Access Token: ')
        self.e1 = tk.Entry(self, width=50)
        self.e2 = tk.Entry(self, width=50)
        self.e3 = tk.Entry(self, width=50)
        self.e4 = tk.Entry(self, width=50)
        but1 = tk.Button(self, text='Create Config File', command=lambda: self.createPickle())
        but2 = tk.Button(self, text='Return to previous page', command=lambda: self.controller.show_frame(FirstPage))
        
        lab1.grid(row=0, column=0)
        lab2.grid(row=1, column=0)
        lab3.grid(row=2, column=0)
        lab4.grid(row=3, column=0)
        self.e1.grid(row=0, column=1)
        self.e2.grid(row=1, column=1)
        self.e3.grid(row=2, column=1)
        self.e4.grid(row=3, column=1)
        but1.grid(row=4, column=0)
        but2.grid(row=4, column=1)
    
    def createPickle(self):
        outfile = open('Configs.pkl', 'wb')
        rURL = self.e1.get()
        apiURL = self.e2.get()
        accnt = self.e3.get()
        tok = self.e4.get()
        pickle.dump(rURL, outfile)
        pickle.dump(apiURL, outfile)
        pickle.dump(accnt, outfile)
        pickle.dump(tok, outfile)
        outfile.close()
        messagebox.showinfo(message='Config File Created')


class PageTwo(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)
        self.controller = controller
        lab1 = tk.Label(self, text='Account configuration loaded')
        lab2 = tk.Label(self, text='Please enter your course ID #: ')
        e1 = tk.Entry(self)
        but1 = tk.Button(self, text='Set Course', command=lambda: self.controller.getCourseTitle(e1.get()))
        lab1.grid(row=0,column=0)
        lab2.grid(row=1,column=0)
        e1.grid(row=1,column=2)
        but1.grid(row=2,column=0)
    
    
class PageThree(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)
        self.controller = controller
        lab1 = tk.Label(self, text='Account configuaration loaded')
        lab2 = tk.Label(self, text='Course: ')
        lab3 = tk.Label(self, textvariable=self.controller.app_data['courseTitle'])
        but1 = tk.Button(self, text='Get Data from Canvas', command=lambda: self.controller.buildGradebook(self.controller.app_data['courseID'].get()))       
        
        lab1.grid(row=0,column=0)
        lab2.grid(row=1,column=0)
        lab3.grid(row=2,column=0)
        but1.grid(row=3,column=0)
        
        
class PageFour(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)
        self.controller = controller
        lab1 = tk.Label(self, text='Data is ready to send to students')
        but1 = tk.Button(self, text='Preview message', command=lambda: self.controller.genPreviewMessage())
        but2 = tk.Button(self, text='Send to students', command=lambda: self.controller.genMessages())
        but3 = tk.Button(self, text='Create teacher report', command=lambda: self.controller.genTeachReport())
        
        lab1.grid(row=0,column=0)
        but1.grid(row=1,column=0)
        but2.grid(row=2,column=0)
        but3.grid(row=3,column=0)
        
        
class PageFive(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)
        self.controller = controller
        lab1 = tk.Label(self, text='Messages sent! Students will find them in their Canvas inbox.')
        lab1.grid(row=0, column=0)
        but1 = tk.Button(self, text='Close program.', command=lambda: self.controller.closeProgram())
        but1.grid(row=1, column=0)
        

class StudentPreview(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)
        self.controller = controller
        self.t1 = tk.Text(self, width=40, height=10, wrap='word')
        but1 = tk.Button(self, text='Return', command=lambda: self.controller.show_frame(PageFour))
        but2 = tk.Button(self, text='Display Preview Text', command=lambda: self.showText())        
        self.t1.grid(row=0,column=0)
        but1.grid(row=1,column=0)
        but2.grid(row=1,column=1)
        
    def showText(self):
        self.t1.insert('1.0', self.controller.preview)



app = SBGApp()
app.wm_title('Canvas Power-Standard Score Generator')
app.mainloop()
