# URLEXT

多线程爬取并筛选登录后台的静态爬虫，子域名放到sub.domain.txt，运行

EX:
- `bash run.sh 项目名称`
- `./run.sh 内部测试项目`

---

通过bash脚本每个子域名对应一个后台进程，默认10线程爬取页面href等链接，白名单黑名单共同筛选后台登录页面，动态生成筛选后的html报告至filter_report目录。