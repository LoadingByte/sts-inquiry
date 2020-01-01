# Sts Inquiry

StellwerkSim Inquiry is a powerful web-based search engine for the railway signal boxes from the game [StellwerkSim](https://www.stellwerksim.de/).
It is written in Python 3 and, because the game is only available in German, its UI also uses the German language.

A production instance of the webapp is permanently hosted at https://loadingbyte.com/sts-inquiry. Check it out!

## Install

If, for some reason, you don't want to use the official hosted instance and instead want to set up your own,
feel free to do so by first cloning the code:

    $ git clone https://github.com/LoadingByte/sts-inquiry
    $ cd sts-inquiry

Make sure you have a recent version of Python 3 installed.
You can now quickly deploy Sts Inquiry, e.g., using a virtualenv and [Gunicorn](https://gunicorn.org/):

    $ virtualenv3 venv
    $ source venv/bin/activate
    $ pip install gunicorn -r requirements.txt
    $ gunicorn -b 127.0.0.1:4000 sts_inquiry:app

## Configure

Although Sts Inquiry already functions without manual configuration, there are cases in which you might want to change the config,
e.g., if you want to use a different application root.
To do that, copy the config file from `sts_inquiry/settings.cfg` to some new place and change the settings there.
When you start the app in the future, simply supply the path to your new config file
in the environment variable `STS_INQUIRY_SETTINGS`:

    $ STS_INQUIRY_SETTINGS=/path/to/new/settings.cfg gunicorn -b 127.0.0.1:4000 sts_inquiry:app
