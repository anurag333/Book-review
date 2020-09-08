import os
import csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")


engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open('books.csv')
    reader = csv.reader(f)
    cnt=0;
    for row in reader:
        
        isbn = row[0]
        title = row[1]
        author = row[2]
        year = row[3]
        cnt+=1
        print(cnt)
        if cnt>1:
            db.execute("INSERT INTO book (isbn,title,author,year) VALUES(:isbn,:title,:author,:year)",{"isbn":isbn,"title":title,"author":author,"year":int(year)})
    db.commit()
    print("complete")



if __name__ == "__main__":
    main()
