import urllib2, cookielib, urllib, sys, re, os.path, json
from cookielib import CookieJar
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint
from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class MyHTMLParser(HTMLParser):
    isIframe = False
    isTable = False
    isTitle = False
    isOpened = False
    isJobNum = False
    isLocation = False
    isForm = False
    isFormNeeded = False
    isICSID = False
    hnewper = False
    tableCnt = 0
    data = {'posting_table_string':'', 'jobs':[]}
    row = {}
    re_ptitle = re.compile('^POSTINGTITLE\$[0-9]+')
    re_popened = re.compile('^OPENED\$[0-9]+')
    re_jobnum = re.compile('^JOBNUMBER\$[0-9]+')
    re_location = re.compile('^HRS_LOCATION_DESCR\$[0-9]+')
    def tagToString(self, tag, attrs):
        ret = '<' + tag + ' '
        for attr in attrs:
            ret += attr[0] + '=' + attr[1] + ' '
        ret += '>'
        return ret
    def handle_starttag(self, tag, attrs): 
        if tag == 'iframe':
            for attr in attrs:
                if attr[0] == 'id' and attr[1] == 'ptifrmtgtframe':
                    self.isIframe = True;
                if attr[0] == 'src' and self.isIframe:
                    self.data['posting_page_src'] = attr[1]
                    self.isIframe = False
        if tag == 'table':
            self.tableCnt = self.tableCnt + 1
            for attr in attrs:
                if attr[0] == 'id' and attr[1] == 'ACE_HRS_APPL_WRK_HRS_JOB_POST_GPB':
                    self.isTable = True
        if tag == 'a':
            for attr in attrs:
                if attr[0] == 'id' and self.re_ptitle.match(attr[1]):
                    self.isTitle = True
        if tag == 'span':
            for attr in attrs:
                if attr[0] == 'id':
                    if self.re_popened.match(attr[1]):
                        self.isOpened = True
                    elif self.re_jobnum.match(attr[1]):
                        self.isJobNum = True
                    elif self.re_location.match(attr[1]):
                        self.isLocation = True
        if tag == 'form':
            self.isForm = True
            for attr in attrs:
                if attr[0] == 'name' and attr[1] == 'win0':
                    self.isFormNeeded = True
                if attr[0] == 'action' and self.isFormNeeded:
                    self.data['form_action'] = attr[1]
        if tag == 'input':
            for attr in attrs:
                if attr[0] == 'name':
                    if attr[1] == 'ICSID':
                        self.isICSID = True
                    if attr[1] == 'HRS_CE_JO_EXT_I$hnewpers$0':
                        self.hnewper = True
                    print '\033[95m Input Name: {0}'.format(attr[1])
                if attr[0] == 'value':
                    if self.isICSID:
                        self.data['ICSID'] = attr[1]
                        self.isICSID = False
                    if self.hnewper:
                        self.data['hnewper'] = attr[1]
                        self.hnewper = False
                    print '\033[93m Input value: {0}'.format(attr[1])
        if self.isTable:
            self.data['posting_table_string'] += self.tagToString(tag, attrs)
    def handle_data(self, data): 
        if self.isTable:
            self.data['posting_table_string'] += data
        if self.isTitle:
            if 'title' in self.row:
                self.row['title'] += data
            else:
                self.row['title'] = data
        if self.isOpened:
            self.row['date'] = data
        if self.isJobNum:
            self.row['job_id'] = data
        if self.isLocation:
            self.row['location'] = data
    def handle_endtag(self, tag):
        if self.isTable:
            self.data['posting_table_string'] += '</' + tag + '>'
        if tag == 'table':
            self.tableCnt = self.tableCnt - 1
            if self.tableCnt <= 0:
                self.isTable = False
        if tag == 'a' and self.isTitle:
            self.isTitle = False;
        if tag == 'span':
            if self.isOpened:
                self.isOpened = False
            elif self.isJobNum:
                self.isJobNum = False
            elif self.isLocation:
                self.isLocation = False
                self.data['jobs'].append(self.row)
                self.row = {}
        if tag == 'form':
            self.isForm = False
            self.isFormNeeded = False


def main(argv):
    url = 'https://zhr-candidate.shared.utsystem.edu/psp/ZHRPRDCG/EMPLOYEE/HRMS/c/HRS_HRAM.HRS_CE.GBL/?tab=PAPP_GUEST&SiteId=8'
    cj = CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    urllib2.install_opener(opener)
    response = urllib2.urlopen(url)
    html = response.read()
    parser = MyHTMLParser()
    parser.feed(html)
    response = urllib2.urlopen(parser.data['posting_page_src'])
    html = response.read()
    parser.feed(html)
    form_values = {
        "ICAJAX" : "1",
        "ICNAVTYPEDROPDOWN" : "1",
        "ICType" : "Panel",
        "ICElementNum" : "0",
        "ICStateNum" : "5",
        "ICAction" : "HRS_APPL_WRK_HRS_LST_NEXT",
        "ICXPos" : "0",
        "ICYPos" : "0",
        "ResponsetoDiffFrame" : "-1",
        "TargetFrameName" : "None",
        "FacePath" : "None",
        "ICFocus" : "",
        "ICSaveWarningFilter" : "0",
        "ICChanged" : "-1",
        "ICResubmit" : "0",
        "ICSID" : parser.data['ICSID'],
        "ICActionPrompt" : "false",
        "ICFind" : "",
        "ICAddCount" : "",
        "ICAPPCLSDATA" : "",
        "HRS_CE_JO_EXT_I$hnewpers$0":parser.data['hnewper'],
        "HRS_APP_SRCHDRV_HRS_APP_KEYWORD" : "",
        "HRS_APP_SRCHDRV_HRS_POSTED_WTN" : "M",
        "HRS_APPL_WRK_HRS_OPRNAME" : "",
        "HRS_APPL_WRK_HRS_OPRPSWD" : "",
        "SEELCT$chk$0":"N", 
        "SEELCT$chk$1":"N",
        "SEELCT$chk$2":"N",
        "SEELCT$chk$3":"N",
        "SEELCT$chk$4":"N"
    }
    data = urllib.urlencode(form_values)
    response = urllib2.urlopen(parser.data['form_action'], data)
    html = response.read()
    parser.feed(html)
    jls = {"data":[{"date":"","title":"" }]}
    if os.path.isfile('/home/theusbar/utrg_jobs/job_listing.json'):
        jlf = open('/home/theusbar/utrg_jobs/job_listing.json', 'r')
        jls = json.load(jlf)
        jlf.close()
    f = open('/home/theusbar/utrg_jobs/job_listing.json', 'w')
    f.write("{\"data\": " + json.dumps(parser.data['jobs']) + "}")
    f.close()
    if jls['data'][0]['date'] != parser.data['jobs'][0]['date'] and jls['data'][0]['title'] != parser.data['jobs'][0]['title']:
        from_add = 'sendmail_theusbar@web310.webfaction.com'
        to_add = ['xirdneh@gmail.com', 'balandranocoronej@utpa.edu']
        s = SMTP()
        s.connect('smtp.webfaction.com')
        s.login('theusbar', 'tsmbat')
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Job Listing"
        msg['From'] = from_add
        msg['To'] = 'xirdneh@gmail.com'
        txt_msg = '--Date-- | --Job title-- | --Job ID-- | --Location--'
        for job in parser.data['jobs']:
            txt_msg += job['date'] + '|' + job['title'] + '|' + job['job_id'] + '|' + job['location'] + '|'
        html_msg = '<html><head></head><body>'
        html_msg = '<table><thead><tr><td>Date</td><td>Job Title</td><td>Job ID</td><td>Location</td></tr></thead><tbody>'
        for job in parser.data['jobs']:
            html_msg += '<tr><td>' + job['date'] + '</td><td>' + job['title'] + '</td><td>' + job['job_id'] + '</td><td>' + job['location'] + '</td></tr>'
        html_msg += '</tbody></table></body></html>'
        part1 = MIMEText(txt_msg, 'plain')
        part2 = MIMEText(html_msg, 'html')
        msg.attach(part1)
        msg.attach(part2)
        s.sendmail(from_add, to_add, msg.as_string())
        print "Message Set"

if __name__ == "__main__":
    main(sys.argv[1:])
