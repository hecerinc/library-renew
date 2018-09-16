import requests
import os
import sys
import datetime
from bs4 import BeautifulSoup
import smtplib

pin = os.environ.get('_RENEWER_PIN') # pin
username = "Rincon" # name
matricula = "A01088760" # code
url = "https://millenium.itesm.mx/patroninfo~S63*spi/868730/items"
login_url = "https://millenium.itesm.mx/patroninfo*spi"


if pin == None:
    print("No PIN found in environment vars. Please set _RENEWER_PIN")
    raise SystemExit 


# Login first to get the cookies
logindata = {
    'pin': pin,
    'name': username,
    'code': matricula
}

def main():
    r1 = requests.post(login_url, data=logindata, allow_redirects = False)

    cookie_jar = None

    if r1.status_code == 302:
        # Success! get the cookies
        cookie_jar = r1.cookies
    else:
        print("Login request failed", file=sys.stderr)
        raise SystemExit


    # Get renewables
    r2 = requests.get(url, cookies=cookie_jar)
    if r2.status_code != 200:
        print("{}\tFailed to get list of items".format(datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc,microsecond=0).isoformat()), file=sys.stderr)
        raise SystemExit

    soup = BeautifulSoup(r2.text, 'html.parser')
    # Find all .patFuncEntry
    # renewid = .patFuncMark > input[type="checkbox"]
    # For each entry, check if the 
    entries = soup.select(".patFuncEntry")
    renew_list = []
    for entry in entries:
        duedate = entry.select(".patFuncStatus")
        duedate = duedate[0].contents[0].strip()
        duedate = duedate.split(' ')[1]
        duedate =  datetime.datetime.strptime(duedate, "%d-%m-%y")
        today = datetime.datetime.today()
        if today < duedate:
            continue

        mark = entry.select(".patFuncMark")
        renew_key = mark[0].contents[0]['name']
        renew_val = mark[0].contents[0]['value']
        renew_list.append({renew_key: renew_val})
    if len(renew_list) != 0:
        renew(renew_list)

def sendemail(from_addr, to_addr_list, cc_addr_list, subject, message, login, password, smtpserver='smtp.gmail.com:587'):
    header  = 'From: {}\r\n'.format(from_addr)
    header += 'To: {}\r\n'.format(','.join(to_addr_list))
    header += 'Content-type: text/html\r\n'
    header += 'Subject: {}\r\n\r\n'.format(subject)
    message = header + message

    server = smtplib.SMTP(smtpserver)
    server.starttls()
    server.login(login,password)
    problems = server.sendmail(from_addr, to_addr_list, message)
    server.quit()

def sendErrorMessage(errorlist):
    email = os.environ.get('_RENEWER_EMAIL')
    password = os.environ.get('_RENEWER_PASS')
    if email == None or password == None:
        print("{}\tMAILER: Email username or password not found in environment".format(datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc,microsecond=0).isoformat()), file=sys.stderr)
        raise SystemExit
    msg = "<h1>Error renewing books</h1><br /> <br /> <p>Some books failed to renew with the following errors: <br /> <br /> {} </p>".format('<br>'.join([x.string for x in errorlist]))
    sendemail("hecerinc@gmail.com", ["hecerinc@outlook.com"], None, 'Library renewer message', msg, email, password)

def renew(renew_list):
    data = {'currentsortorder': 'current_checkout', 'renewsome': 'SI'}
    data = {**data, **renew_list}
    res = requests.post(url, data=data, cookies=cookie_jar)
    # Check if renew was successfull
    if res.status_code != 200:
        print("{}\tRenew failed with statuscode != 200".format(datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc,microsecond=0).isoformat()), file=sys.stderr)
        raise SystemExit

    soup2 = BeautifulSoup(res.text, 'html.parser')
    errormsg = soup2.find("#renewfailmsg") 
    if errormsg != None:
        # Print an error message
        # Send an email
        errorlist = soup2.select(".patFuncStatus em")
        sendErrorMessage(errorlist)


if __name__ == '__main__':
    main()



