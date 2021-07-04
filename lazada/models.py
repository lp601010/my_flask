import arrow
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from flask import Flask, url_for, render_template, redirect, make_response
import os
from flask_login import LoginManager
import pymysql
import json
import xlsxwriter

def create_mysql_ORM(app):
    """
    创建MySQL的ORM对象并反射数据库中已存在的表，获取所有存在的表对象
    :param app: app:flask实例
    :return: (db:orm-obj, all_table:数据库中所有已存在的表的对象(dict))
    """
    # 创建mysql连接对象
    # url = get_mysql_conn_url(config=app.config)
    url = 'mysql+pymysql://root:admin@127.0.0.1:3306/lazada_ad?charset=utf8'
    app.config["SQLALCHEMY_DATABASE_URI"] = url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True  # 每次请求结束时自动commit数据库修改
    app.config["SQLALCHEMY_ECHO"] = False  # 如果设置成 True，SQLAlchemy将会记录所有发到标准输出(stderr)的语句,这对调试很有帮助.
    app.config["SQLALCHEMY_RECORD_QUERIES"] = None  # 可以用于显式地禁用或者启用查询记录。查询记录 在调试或者测试模式下自动启用。
    app.config["SQLALCHEMY_POOL_SIZE"] = 10  # 数据库连接池的大小。默认是数据库引擎的默认值(通常是 5)。
    app.config["SQLALCHEMY_POOL_TIMEOUT"] = 10  # 指定数据库连接池的超时时间。默认是 10。
    app.config['SECRET_KEY'] = 'you-will-never-guess'
    """
    自动回收连接的秒数。
    这对 MySQL 是必须的，默认 情况下 MySQL 会自动移除闲置 8 小时或者以上的连接。 
    需要注意地是如果使用 MySQL 的话， Flask-SQLAlchemy 会自动地设置这个值为 2 小时。
    """
    app.config["SQLALCHEMY_POOL_RECYCLE"] = None
    """
    控制在连接池达到最大值后可以创建的连接数。
    当这些额外的 连接回收到连接池后将会被断开和抛弃。
    """
    app.config["SQLALCHEMY_MAX_OVERFLOW"] = None
    # 获取SQLAlchemy实例对象
    db = SQLAlchemy(app)

    # 反射数据库中已存在的表，并获取所有存在的表对象。
    db.reflect()
    all_table = {table_obj.name: table_obj for table_obj in db.get_tables_for_bind()}

    # all_table 即是包含所有已存在表对象的字典
    return db, all_table


app = Flask(__name__)
db, all_table = create_mysql_ORM(app=app)


class User(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    password = db.Column(db.String(64))
    realname = db.Column(db.String(64))
    role = db.Column(db.SmallInteger, default=0)
    last_seen = db.Column(db.DateTime)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def __repr__(self):
        return '<User %r>' % (self.username)

    @classmethod
    def login_check(cls, username, password):
        user = cls.query.filter(db.and_(User.username == username, User.password == password)).first()
        if not user:
            return None
        return user


from flask_wtf import FlaskForm as Form
from wtforms.fields import StringField, TextField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import Length, DataRequired
import io
import time
class GetData:
    def __init__(self,month):
        base = db.session.execute(f'''
            SELECT
                 *
                 FROM lazada_ad.base_data  where  date_format(业绩年月, '%Y%m')  = '{month}'
                ''')
        df = pd.DataFrame(columns=base.keys(), data=base)
        df.rename(columns={"实际总毛利对比(正值为毛利增加)": "实际总毛利对比"}, inplace=True)
        df['业绩年月'] = df['业绩年月'].map(lambda x: arrow.get(x).format('YYYY-MM'))
        self.data = df

    def __call__(self,month):
        df = self.data
        out = io.BytesIO()
        writer = pd.ExcelWriter(out, engine='xlsxwriter')
        df.to_excel(excel_writer=writer, index=False, sheet_name='示例')
        writer.save()
        writer.close()
        # file_name = time.strftime('%Y%m%d', time.localtime(time.time())) + '.xlsx'
        file_name='lazada_base_data_'+month+'.xlsx'
        response = make_response(out.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=%s" % file_name
        response.headers["Content-type"] = "application/x-xls"
        """ 如果输出的是 csv 文件
        df = self.data
        out = io.StringIO()
        df.to_csv(out, index=False)
        file_name = time.strftime('%Y%m%d', time.localtime(time.time())) + '.csv'
        response = make_response(out.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=%s" %file_name
        response.headers["Content-type"] = "text/csv"
        """
        return response

class Submit(Form):
    submit = SubmitField('提取上月数据')

class LoginForm(Form):
    username = StringField(validators=[DataRequired(), Length(max=15)])
    password = StringField(validators=[DataRequired(), Length(max=15)])
    submit = SubmitField('登录')


class SignUpForm(Form):
    username = StringField(validators=[DataRequired(), Length(max=15)])
    password = StringField(validators=[DataRequired(), Length(max=15)])
    realname = StringField(validators=[DataRequired(), Length(max=15)])
    submit = SubmitField('注册')

def read_file(user_path,zd):
    import gc
    try:
        today = time.strftime("%Y%m%d")[-6:]
        zd_str = "'" + zd + "'"
        root_path = os.path.join(user_path,'lazada直通车月数据', zd[:-3], zd)
        for root, folds, files in os.walk(root_path):
            for item in files:
                if "$" not in item and 'Dashboard' in item:
                    br = pd.read_excel(root + '/' + item, header=None)
                    br = br.iloc[6:7, 0:6]
                    br.columns = ['account_Revenue', 'Product_Visitors', 'Buyers', 'Orders', 'Pageviews', 'br_Units_Sold']
                    br['account_Revenue'] = br['account_Revenue'].map(lambda x: str(x)).astype('double')
                elif "$" not in item and '--' in item:
                    ad = pd.read_excel(root + '/' + item)
                    ad = ad[['Placement', 'Spend', 'Impression', 'Clicks', 'Store Orders',
                             'Store Units Sold', 'Store Revenue']]
                    ad[["Spend", "Store Revenue"]] = ad[
                        ["Spend", "Store Revenue"]].applymap(lambda x: str(x)).astype('double')
                    ad[['Impression', 'Clicks', 'Store Orders', 'Store Units Sold']] = ad[
                        ['Impression', 'Clicks', 'Store Orders', 'Store Units Sold']].applymap(lambda x: str(x)).astype(
                        int)
        tmp = ad[
            ['Spend', 'Impression', 'Clicks', 'Store Orders', 'Store Units Sold', 'Store Revenue']].sum().to_frame()
        sumby_ad = pd.DataFrame(tmp.values.T, index=tmp.columns, columns=tmp.index)
        sumby_ad['account'] = zd
        br['account'] = zd
        cpc = pd.merge(sumby_ad, br, on='account')
        cpc['account_Revenue'] = round(cpc['account_Revenue'], 2)
        cpc['Store Revenue'] = round(cpc['Store Revenue'], 2)
        cpc['cr'] = round(cpc['Store Units Sold'] / cpc['Clicks'], 2)
        cpc['cpc'] = round(cpc['Spend'] / cpc['Clicks'], 2)
        cpc['roi'] = round(cpc['Store Revenue'] / cpc['Spend'], 2)
        cpc['update_time'] = today
        cpc.columns = list(map(
            lambda x: x.replace(' ', '_').replace('Store_', '').replace('Impression', 'Impressions').replace(
                'Units_sold',
                'Units_Sold'),
            list(cpc.columns)))
        cpc = cpc[['account', 'Revenue', 'Spend', 'Clicks', 'Units_Sold', 'Impressions', 'account_Revenue',
                   'Product_Visitors',
                   'Buyers', 'Orders', 'br_Units_Sold', 'Pageviews',
                   'cr', 'cpc', 'roi', 'update_time']]
        # 上传月数据
        try:
            db.session.execute("delete from lazada_ad.cpc_month_data where account=%s" % (zd_str))
            db.session.commit()
        except:
            pass
        cpc.to_sql(name='cpc_month_data', con=db.get_engine(), if_exists='append', index=False)
        # sumby_ad = ad.groupby(['Placement'], as_index=False)['Spend', 'Impression', 'Clicks', 'Store Orders', 'Store Units Sold', 'Store Revenue'].sum()
        # sumby_ad['account'] = zd
        # br['account'] = zd
        # ssp = pd.merge(sumby_ad, br, on='account')
        # ssp['account_Revenue'] = round(ssp['account_Revenue'], 2)
        # ssp['Store Revenue'] = round(ssp['Store Revenue'], 2)
        # ssp['cr'] = round(ssp['Store Units Sold'] / ssp['Clicks'], 2)
        # ssp['cpc'] = round(ssp['Spend'] / ssp['Clicks'], 2)
        # ssp['roi'] = round(ssp['Store Revenue'] / ssp['Spend'], 2)
        # ssp['update_time'] = today
        # ssp.columns = list(map(
        #     lambda x: x.replace(' ', '_').replace('Store_', '').replace('Impression', 'Impressions').replace('Units_sold',
        #                                                                                                      'Units_Sold'),
        #     list(ssp.columns)))
        # ss = ssp[ssp['Placement'] == 'Sponsored Search'][
        #     ['account', 'Revenue', 'Spend', 'Clicks', 'Units_Sold', 'Impressions', 'account_Revenue', 'Product_Visitors',
        #      'Buyers', 'Orders', 'br_Units_Sold','Pageviews',
        #      'cr', 'cpc', 'roi', 'update_time']]
        # sp = ssp[ssp['Placement'] == 'Sponsored Products'][
        #     ['account', 'Revenue', 'Spend', 'Clicks', 'Units_Sold', 'Impressions', 'account_Revenue', 'Product_Visitors',
        #      'Buyers', 'Orders', 'br_Units_Sold','Pageviews',
        #      'cr', 'cpc', 'roi', 'update_time']]
        # # 上传月数据
        # try:
        #     db.session.execute("delete from lazada_ad.ss_month_data where account=%s" % (zd_str))
        #     db.session.execute("delete from lazada_ad.sp_month_data where account=%s" % (zd_str))
        #     db.session.commit()
        # except:
        #     pass
        # ss.to_sql(name='ss_month_data', con=db.get_engine(), if_exists='append', index=False)
        # sp.to_sql(name='sp_month_data', con=db.get_engine(), if_exists='append', index=False)
    except Exception as e:
        raise Exception
    finally:
        gc.collect()
        return

import zipfile
def zip_files(f,user_path):
    zip_file = zipfile.ZipFile(f, 'r')
    zip_file.extractall(path=user_path)
    for root, folds, files in os.walk(user_path):
        for item in folds:
            old_name = os.path.join(root, item)
            new_name = os.path.join(root, item.encode('cp437').decode('gbk'))
            os.rename(old_name, new_name)
    zip_file.close()

if __name__ == '__main__':
    print(123)
# 聂小倩
#     br=pd.read_excel(r'C:\Users\Administrator\Desktop\工作簿1.xlsx',sheet_name='Sheet1')
#     li=br['标题'].map(lambda x:x.split(']')[0])
#     for index, value in enumerate(li):
#         if li[index] == li[index + 1]:
#             print(index+2, br['标题'][index])

    # db.create_all(

# json格式
    # base = db.session.execute(f'''
    #     SELECT
    #          *
    #          FROM lazada_ad.base_data  where  date_format(业绩年月, '%Y%m')  = '202101'
    #         ''')
    # df = pd.DataFrame(columns=base.keys(), data=base)
    # df.rename(columns={"实际总毛利对比(正值为毛利增加)": "实际总毛利对比"}, inplace=True)
    # df['业绩年月'] = df['业绩年月'].map(lambda x: arrow.get(x).format('YYYY-MM'))
    # df.to_excel("D:\lazada广告基础数据01月.xlsx", index=False)

    # base = db.session.execute(f'''
    #   SELECT 广告类型,业绩年月,sum(广告花费) 广告花费,sum(广告销售额) 广告销售额 FROM lazada_ad.base_data group by 广告类型,业绩年月 order by 业绩年月,广告类型
    #         ''')
    # df = pd.DataFrame(columns=base.keys(), data=base)
    # j = df.to_json(orient="values", force_ascii=False)
    # j=df.to_json(orient="records", force_ascii=False)
    # df.to_json(orient="values", force_ascii=False)
    # df.to_json(orient="columns", force_ascii=False)
    # di=dict.fromkeys(base.keys(), base.fetchall())
    # print(di)
    # j1=json.dumps(di.__str__())
    # j = df.to_dict(orient="records")
    # j = json.dumps(j)

# echatrs
#     base = db.session.execute(f'''
#         SELECT * FROM lazada_ad.base_data where 业绩年月='2021-03-01 00:00:00' and 广告接手人= '余孟济'
#             ''')
#     df = pd.DataFrame(columns=base.keys(), data=base)
#     df.sample(frac=0.33).reset_index(drop=True)


    # df = pd.melt(df, id_vars='二级类目', var_name='时间', value_name='销售额')
    # df = df[df['销售额'] != 0.000000]
    # df = df[['时间', '二级类目', '销售额']]
    # df['时间'] = df['时间'].map(lambda x: x.strip('销售额'))
    # df['销售额'] = df['销售额'].astype('int')
    # df['二级类目'] = df['二级类目'].fillna(value='其他')
    # df = df.groupby(['时间', '二级类目'], as_index=False)['销售额'].sum()
    # df = df.sort_values(by='时间').sort_values(by='二级类目', ascending=False)
    # df = df[df['销售额'] > 1000]