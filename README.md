# Crawler Project

## Setup

1. Prerequisites: Have python3, virtualenv and pip installed.
1. Create a virtual environment: run `virtualenv venv` in the crawler
   project folder.
1. Activate the virtual environment: `. ./venv/bin/activate`
1. Install the project dependencies: `pip install -r requirements.txt`

## Running the Crawler

Execute the following command:

```
python3 crawler.py --root_url=YOUR_SITE_ROOT_URL
```

where `YOUR_SITE_ROOT_URL` is the full URL for your site, e.g.,
`http://www.joanorr.com`.

## Testing the Crawler

Execute

```
pytest test_crawler.py
```
