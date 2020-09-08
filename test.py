import requests
from bs4 import BeautifulSoup
v = '0590353403'
page = requests.get(f"https://www.goodreads.com/book/isbn/{v}")

soup = BeautifulSoup(page.text,features="html.parser")
tag = soup.find("img", id="coverImage")
tag = str(tag)

start = tag.find("https:")
end = tag.find("/>")
print(tag[start:end-1])