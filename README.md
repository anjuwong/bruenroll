# BruEnroll
## Enrollment statistics for UCLA
This is a tool I developed to scrape the [UCLA registrar
pages](http://www.registrar.ucla.edu) for class
enrollment, among other public data on those pages. This project is a rewrite of
the project found [here](https://github.com/anjuwong/clsc), formatted a bit more
nicely, using MongoDB instead of MySQL, and with a front-end written with Python
instead of PHP.

![ScreenShot](/page.png)

With enough data, this tool could be used to conclude things like:
1. When to sign up for classes (given that UCLA uses a two-pass system for enrollment)
2. How difficult a course is (a more objective measure, drops throughout the quarter, rather than subjective ratings)
3. The likelihood a given class will increase enrollment past its original cap
