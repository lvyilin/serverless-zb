基于AWS Lambda的无服务器 (Serverless) 数据标注众包平台
==============================================

一个具有数据标注功能的众包平台，用户可以上传数据集，添加协作者，在平台上合作完成数据标注任务，并导出标注结果。

后台使用 AWS Lambda、Amazon API Gateway部署无服务器应用程序，Amazon DynamoDB、Amazon S3作为数据库与储存容器，使用Amazon Cognito建立用户池。
前后端使用RESTful API进行交互。

功能
-----------

+ 支持文本标注
+ 登录，注册，验证邮箱，注销
+ 上传(/列出/删除)数据集
+ 添加(/删除)合作者
+ 查看数据集内数据
+ 标注数据
+ 导出标注结果
