#AskCanary: Share Real Estate Data On-Demand in Slack

##Description:
The inspiration of this project comes from a discussion my family had when my sister was purchasing a house. While looking for a house, communication between family members and their real estate agent is important. I would say it is even more so for full time real estate professionals and businesses.
For individuals like that, they are often on the go and often only carrying a phone. What's a great way to stay on the go, utilize the on-demand data provided by HouseCanary, and be able share the information with other house/team members? That's when I thought of incorporating HouseCanary API with Slack.
The slackbot @askcanary will display the property data requested on demand using HouseCanary's Analytic API. Not only can Slack members view the data at the same time, the same information can be email to non-Slack users using the command "@askcanary email".

##Environment Variables
* HC_API_KEY
* HC_API_SECRET
* BOT_ID
* SLACK_BOT_TOKEN
* SENDGRID_API_KEY
* FROM_EMAIL

##Slackbot Queries:
* First user enter "@askcanary address: 123 StreetName". 
* @askcanary provides a list of options once zipcode's entered. User can then search for data by entering a search option, such as "@askcanary school" to get nearby school data. 
* If they want to email the data instead, they just enter "@askcanary email receiver@email.com as their_own_name with school".
* To exit and restart at anytime, just enter "@askcanary exit"!

##Sample Pictures
Here are some test input. Once address and zipcode are entered, slackbot will detect duplicate entries. To search for another property, user should enter @askcanary exit first. Once both address and zipcode are in, Slackbot tells users what their options are, such as searching for school data near the address:
![Property Data Input](https://github.com/amychan331/hackathon-askcanary/blob/master/image/property_data_input.png)
User can also email the property data. User name is included in the email subject line so the receiver can see who sent it, along with the property address and zipcode in the email body message. In addition to property data, user can also search for value report and even get it in summary verions:
![Email and Value Report](https://github.com/amychan331/hackathon-askcanary/blob/master/image/email_and_value_report.png)
Another email send, this time with the value report in summary version. Once that's done, I exited. As noted, address and zipcode is no longer stored, so attempted at input of zipcode or other property inquiry will result in an error message by @askcanary:
![Exit and Error](https://github.com/amychan331/hackathon-askcanary/blob/master/image/exit_and_error.png)