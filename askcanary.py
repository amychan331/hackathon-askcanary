import os
import time
import re
import json
import base64
from slackclient import SlackClient
import housecanary
import sendgrid
from sendgrid.helpers.mail import *


# Set constant and API-related varialbes
BOT_ID = os.environ.get("BOT_ID")
AT_BOT = "<@" + BOT_ID + "> "
slack_client = SlackClient(os.environ.get("SLACK_BOT_TOKEN"))
housecanary_client = housecanary.ApiClient()
sendgrid_client = sendgrid.SendGridAPIClient(apikey=os.environ.get("SENDGRID_API_KEY"))
from_email = Email(os.environ.get("FROM_EMAIL"))


def to_sendgrid(email, info, name, attachment_data=False):
    subject = "Property info sent by " + name
    to_email = Email(email)
    content = Content("text/plain", info)
    mail = Mail(from_email, subject, to_email, content)
    if attachment_data:
        attachment_data = base64.b64encode(attachment_data.encode("utf-8"))
        attachment = Attachment()
        attachment.set_content(attachment_data)
        attachment.set_type("application/pdf")
        attachment.set_filename("property_info.pdf")
        attachment.set_disposition("attachment")
        attachment.set_content_id("Property Info")
        mail.add_attachment(attachment)

    try:
        sendgrid_client.client.mail.send.post(request_body=mail.get())
        return "Data successfully sent to " + email +"."
    except Exception as e:
        print str(e)
        return "Email delivery failed. Please try again."


def reformat_json(data):
    data = data.encode('utf-8').replace("],", "").replace("},", "").replace(":", ": ").replace(
        "null", "N/A").translate(None, '{}[]"')
    # Replace & translate leaves empty lines. Following 2 line removes them.
    data = [line for line in data.split("\n") if line.strip()]
    data = "\n".join(data)
    return data


def get_report(data, report_type="full", format_type="json"):
    try:
        response = housecanary_client.property.value_report(data['address'], int(data['zipcode'])
            , report_type, format_type)
    except housecanary.exceptions.RequestException:
        return "nonexistence"
        
    if format_type == "json":
        report = json.dumps(response.json(), indent=4, separators=(',',':'), ensure_ascii=False)
        report = reformat_json(report)
        result = "Value report of " + data['address'] + ", " + data['zipcode'] + ": \n" + report
    else:
        text = "Attached is a " + report_type + " value report for the " \
               "property at " + data['address'] + ", " + data['zipcode'] + "."
        result = [text, response]
    return result


def get_property(cmd, data):
    try:
        # Since many options exist for the endpoint method, a variable stores
        # selected option to be use as attribute for housecanary_client.property call.
        endpoint = cmd.replace(' ', '_')
        call = getattr(housecanary_client.property, endpoint)
        response = call((data['address'], int(data['zipcode'])))
    except housecanary.exceptions.RequestException:
        return "nonexistence"
    
    json_data = json.dumps(response.json()[0]['property/'+endpoint]['result'], 
        indent=4, separators=(',',':'), ensure_ascii=False)
    json_data = reformat_json(json_data)
    result = "The " + cmd + " of " + data['address'] + " is: \n"
    result += json_data
    return result


def get_next_question(cmd, zip=False):
    if not zip:
        question = "What is the zipcode? Answer by entering \"@askcanary " \
        "zipcode: 12345\". Enter \"@askcanary exit\" any time to end your inquiry:"
    else:
        question = "What data would you like? Enter \"@askcanary data_option\"." \
                   "Possible options includes: census, details, flood, mortgage" \
                   " lien, MSA details, NOD, owner occupied, rental value, " \
                   "sales history, school, value, value forecast, zip details, " \
                   "forecast by zip, historical price returns by zip, market " \
                   "volatility by zip, value report, or value report in summary."\
                   "\n\n Want to email the result? Enter \"@askcanary email " \
                   "123@email.com as yourname with data_option\"."
    return question


def get_error(cmd=False, data=False):
    if cmd == "exist":
        error = "Same type of information was already submitted. Enter next " \
                "requested info or \"@askcanary exit\" to restart inquiry."
    elif cmd == "nonexistence":
        error = "Unable to find data for " + data['address'] + ", " + data['zipcode'] + "."
    elif cmd == "addr":
        error = "Address was not input earlier. Enter the address first."
    elif cmd == "nodata":
        error = "There is no input for address and zipcode. Enter those first."
    else:
        error = "Sorry, I can't understand your input."
    return error


def process_cmd(cmd):
    if ':' in cmd:
        if "email" in cmd:
            #slack converts email input to <mailto: someone@google.com|amychan331@google.com>
            #so let's clean that out first, then process everything into list
            clean_cmd = re.sub(r'<mailto.*\|', "", cmd).replace('>', '')
            cmd_list = clean_cmd.split(' with ')
            email_portion = cmd_list[0].split(' ', 3)
            if len(email_portion) == 4:
                result = ["email"]
                result.append(email_portion[1].strip()) #receiver_email
                result.append(email_portion[3].strip()) #your_name
                result.append(cmd_list[1].strip()) #options
            else:
                return "wrong input"
        else:
            result = cmd.split(':', 1)
            result[0] = result[0].lower().strip()
            result[1] = result[1].strip()
    else:
        result = cmd.lower().strip()
    return result


# Method will either return a string to be output # or a dictionary where the
# key will trigger an action upon its return  
def read_input(cmd, data):
    cmd = process_cmd(cmd)
    data_option = ["census", "details", "flood", "mortgage lien", 
        "MSA details", "NOD", "owner occupied", "rental value", 
        "sales history", "school", "value", "value forecast", "zip details", 
        "forecast by zip", "historical price returns by zip", 
        "market volatility by zip"]

    if cmd == "exit":
        response = {"exit": "Thank you for using AskCanary!"}
        return response
    elif cmd[0] == 'address':
        if 'address' in data:
            response = get_error("exist")
            return response
        else:
            response = get_next_question(cmd)
            return {"msg": response, "to_update": {"address": cmd[1]}}
    elif cmd[0] == 'zipcode':
        if 'zipcode' in data:
            response = get_error("exist")
            return response
        elif 'address' not in data:
            return get_error("addr")
        else:
            response = get_next_question(cmd, cmd[1])
            return {"msg": response, "to_update": {"zipcode": cmd[1]}}
    elif 'email' in cmd[0]:
        if 'address' in data and 'zipcode' in data:
            email = cmd[1]
            name = cmd[2]
            #First, check if email is for property option or value report.
            if "value report" in cmd[3]:
                options = cmd[3].split(' in ')

                if len(options) > 1:
                    report_type = "summary" if "summary" in options else "full"
                    format_type = "pdf" if "pdf" in options else "json"
                    info = get_report(data, report_type, format_type)
                else:
                    info = get_report(data)          
            elif cmd[3] in data_option:
                info = get_property(cmd[3], data)
            else:
                return get_error()
            # Second, check if property info exist. 
            # If so, start emailing.
            if info == "nonexistence":
                return get_error(info, data)
            else:
                if isinstance(info, list):
                    text = info[0]
                    attachment_data = info[1]
                    print type(attachment_data)
                    return to_sendgrid(email, text, name, attachment_data)
                else:
                    return to_sendgrid(email, info, name)
        else:
            return get_error("nodata")
    elif cmd in data_option:
        if 'address' in data and 'zipcode' in data:
            prop = get_property(cmd, data)
            if prop == "nonexistence":
                return get_error(prop, data)
            else:
                return prop
        else:
            return get_error("nodata")
    elif "value report" in cmd:
        if 'address' in data and 'zipcode' in data:
            options = cmd.split(' in ')
            report = get_report(data, options[1].strip()) if len(options) > 1 else get_report(data)
            if report == "nonexistence":
                return get_error(report, data)
            else:
                return report
        else:
            return get_error("nodata")
    else:
        return get_error()


def parse_slack_output(slack_rtm_output, channel=False):
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                if channel:
                    return output['text'].split(AT_BOT)[1], output['channel']
                else:
                    return output['text'].split(AT_BOT)[1]
    return None, None


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1
    if slack_client.rtm_connect():
        print "AskCanary connected and running!"
        data = {}
        while True:
            command, channel = parse_slack_output(slack_client.rtm_read(), True)
            if command and channel:
                result = read_input(command, data)
                if isinstance(result, dict):
                    if "exit" in result:
                        try:
                            data = {}
                        except:
                            print "Unable to unset data."
                    else:
                        data.update(result["to_update"])
                        result.pop("to_update")
                    slack_client.api_call("chat.postMessage", channel=channel, 
                        text=list(result.values())[0], as_user=True)
                else: 
                    slack_client.api_call("chat.postMessage", channel=channel, 
                        text=result, as_user=True)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print "Connection failed. Invalid Slack token or bot ID?"
