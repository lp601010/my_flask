from lazada.models import User,db, all_table,app,LoginForm,SignUpForm,Submit, GetData,read_file
import os
import zipfile
import warnings
import time
warnings.filterwarnings("ignore")

import arrow
mn = arrow.now().shift(months=-1).format("YYYYMM")
import pandas as pd
from flask import Flask, render_template, request, Response, jsonify,g,redirect,url_for,flash
from flask_sqlalchemy import SQLAlchemy
from pyecharts import options as opts
from pyecharts.charts import Bar, Line
from pyecharts.globals import ThemeType
from datetime import datetime

from flask_login import LoginManager,login_user, logout_user, current_user, login_required
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = u"请先登录。"
login_manager.init_app(app)



@app.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated:
        g.user.last_seen = datetime.now()
        db.session.add(g.user)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/sign-up',methods=['GET','POST'])
def sign_up():
    form = SignUpForm()
    user = User()
    if form.validate_on_submit():
        user_name = request.form.get('username')
        user_password = request.form.get('password')
        realname = request.form.get('realname')
        register_check = User.query.filter(db.and_(User.username == user_name, User.password == user_password)).first()
        if register_check:
            return redirect('/sign-up')
        if len(user_name) and len(user_password):
            user.username = user_name
            user.password = user_password
            user.realname = realname
            db.session.add(user)
            db.session.commit()
            return redirect('/login')
        return redirect('/login')
    return render_template("sign_up.html", form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.login_check(request.form.get('username'),request.form.get('password'))
        if user:
            login_user(user)
            user.last_seen = datetime.now()
            try:
                db.session.add(user)
                db.session.commit()
            except:
                return redirect('/login')
            return redirect(url_for("index"))
        else:
            return redirect('/sign-up')
    return render_template('login.html',form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/25team', methods=["GET", "POST"])
def test():
    from pyecharts.charts import Line3D,Bar3D,Line
    csv = pd.read_excel(r'C:\Users\Administrator\Downloads\25组（2018-2021年产品和销量）.xlsx')
    df = csv.drop(['小组', 'ASIN', 'SKU', '2018全年度销售额', '2019全年度销售额', '2020全年度销售额', 'ASIN', '一级类目', '三级类目'], axis=1)
    df['二级类目'] = df['二级类目'].fillna(value='其他')
    df = df.groupby(['二级类目'], as_index=True).sum()
    df.drop(df.columns[:15], axis=1, inplace=True)
    df = df.astype('int')
    line = (
        Line()
            .add_xaxis(df.columns.to_list()))
    # .set_global_opts(splitline_opts=opts.SplitLineOpts(is_show=True))
    for index, row in df.iterrows():
        if row.sum()>50000:
            # if index=="其他":
            #     line.add_yaxis(index, row.tolist(), is_selected=True)
            line.add_yaxis(index, row.tolist())

    line.set_series_opts(
                label_opts=opts.LabelOpts(is_show=False)
            ).set_global_opts(
        xaxis_opts=opts.AxisOpts(name="业绩年月",splitline_opts=opts.SplitLineOpts(is_show=True)),
        yaxis_opts=opts.AxisOpts(name="销售额(美元)",splitline_opts=opts.SplitLineOpts(is_show=True)),
        title_opts=opts.TitleOpts("25组销量曲线图")
    )

    # line=(
    #     Line3D()
    #         .add(
    #         "",
    #         data=df.values.tolist(),
    #         xaxis3d_opts=opts.Axis3DOpts(data=df['时间'], type_="category"),
    #         yaxis3d_opts=opts.Axis3DOpts(data=df['二级类目'], type_="category"),
    #         zaxis3d_opts=opts.Axis3DOpts(type_="value")
    #         # grid3d_opts=opts.Grid3DOpts(width=100, height=100, depth=100),
    #     )
    #     .set_global_opts(
    #         xaxis_opts=opts.AxisOpts(name="业绩年月"),  # x轴名称
    #         yaxis_opts=opts.AxisOpts(name="二级类目"),  # y轴名称
    #         # zaxis_opts=opts.AxisOpts(name="销售额"),  # y轴名称
    #     )
    # )
    return render_template('25team.html', myechart=line.render_embed())

@app.route('/', methods=["GET", "POST"])
@login_required
def index():
    base = db.session.execute(f'''
        SELECT case when 广告类型 = '联盟' then '联盟' else 'CPC' end 广告类型,业绩年月,sum(广告花费) 广告花费,sum(广告销售额) 广告销售额 FROM lazada_ad.base_data 
        group by case when 广告类型 = '联盟' then '联盟' else 'CPC' end,业绩年月 order by 业绩年月,广告类型
            ''')
    df = pd.DataFrame(columns=base.keys(), data=base)
    df['业绩年月'] = df['业绩年月'].map(lambda x: arrow.get(x).format('YYYY-MM'))
    df[['广告花费', '广告销售额']] = df[['广告花费', '广告销售额']].astype(int)
    df2 = df.groupby(['业绩年月'], as_index=False)["广告销售额", "广告花费"].sum()
    df2['ROI'] = df2["广告销售额"] / df2["广告花费"]

    df_tmp = pd.DataFrame(data=df[df['广告类型'] == 'CPC']['广告销售额'] / df[df['广告类型'] == 'CPC']['广告花费'])
    df_tmp.index = range(len(df_tmp))

    df_tmp2=pd.DataFrame(data=df[df['广告类型'] == '联盟']['广告销售额'] / df[df['广告类型'] == '联盟']['广告花费'])
    df_tmp2.index = range(len(df_tmp2))


    df2['CPCROI'] = df_tmp
    df2['联盟ROI'] = df_tmp2
    bar = (
        Bar(init_opts=opts.InitOpts(theme=ThemeType.SHINE,
                                    animation_opts=opts.AnimationOpts(animation_easing="elasticOut")))
            .add_xaxis(df.groupby(['业绩年月'])['业绩年月'].first().tolist())
            .add_yaxis("CPC销售额", df[df['广告类型'] == 'CPC'].sort_values(by="业绩年月")["广告销售额"].tolist(), stack="stack1", z=0)
            .add_yaxis("联盟销售额", df[df['广告类型'] == '联盟'].sort_values(by="业绩年月")["广告销售额"].tolist(), stack="stack1", z=0)
            .set_series_opts(
                label_opts=opts.LabelOpts(is_show=False),
                itemstyle_opts={
                    "normal": {
                        "barBorderRadius": [30, 30, 30, 30],
                    }
                }
            )
            .extend_axis(
            yaxis=opts.AxisOpts(
                name="ROI",
                type_="value",
                min_=0,
                max_=30,
                interval=5,
                axislabel_opts=opts.LabelOpts(formatter="{value}"),
            )
        )
            .set_global_opts(
            yaxis_opts=opts.AxisOpts(name="广告销售额",  # y轴名称
                                     axislabel_opts=opts.LabelOpts(formatter="{value} /元")),  # 单位标注
            xaxis_opts=opts.AxisOpts(name="业绩年月"),  # x轴名称
            tooltip_opts=opts.TooltipOpts(
                is_show=True
            )
        )
    )
    line1 = Line().add_xaxis(df.groupby(['业绩年月'])['业绩年月'].first().tolist()).add_yaxis("联盟ROI", df2.sort_values(by="业绩年月")[
        "联盟ROI"].map(lambda x: round(x, 2)).tolist(), yaxis_index=1)
    line2 = Line() \
        .add_xaxis(df.groupby(['业绩年月'])['业绩年月'].first().tolist()) \
        .add_yaxis("总销售额", df2.sort_values(by="业绩年月")["广告销售额"].map(lambda x: round(x, 2)).tolist(), yaxis_index=0,
                   linestyle_opts=opts.LineStyleOpts(opacity=0)) \
        .set_series_opts(
            label_opts=opts.LabelOpts(color='black'),
            itemstyle_opts=opts.ItemStyleOpts(color="black")
        )
    line3 = Line().add_xaxis(df.groupby(['业绩年月'])['业绩年月'].first().tolist()).add_yaxis("CPCROI", df2.sort_values(by="业绩年月")[
        "CPCROI"].map(lambda x: round(x, 2)).tolist(), yaxis_index=1)   \
        .set_series_opts(
            label_opts=opts.LabelOpts(color='#01DFD7'),
            linestyle_opts=opts.LineStyleOpts(color='#01DFD7'),
            itemstyle_opts=opts.ItemStyleOpts(color="#01DFD7")
        )

    bar.overlap(line1)
    bar.overlap(line2)
    bar.overlap(line3)

    form = Submit()
    return render_template('index.html', myechart=bar.render_embed(),g=g,form=form)



@login_required
@app.route('/<ad_type>', methods=["GET", "POST"])
@app.route('/<ad_type>/<host_name>', methods=["GET", "POST"])
def show_table(ad_date=mn, host_name='', ad_type=''):
    if request.form.get('month'):
        ad_date = request.form.get('month')
    if ad_type=='CPC' and  int(ad_date)>=202103:
        if not host_name:
            base = db.session.execute(f'''
                SELECT '合计' 广告类型,业绩年月,sum(广告花费) 广告花费,concat(round(sum(广告花费)/sum(广告销售额)*100,2),'%') acos,sum(广告销售额) 广告销售额,sum(站点销售额)站点销售额,
                  concat(round(sum(广告花费)/sum(站点销售额)*100,2),'%') '广告花费/站点销售额',concat(round(sum(广告销售额)/sum(站点销售额)*100,2),'%') '广告销售额/站点销售额',
                  sum(站点实际利润) 站点实际利润,sum(非广告部分利润) 非广告部分利润,sum(广告利润) 广告利润,sum(广告Click) 广告Click,
                  ROUND((sum(广告花费) / sum(广告Click)),2) CPC,
                  ROUND((sum(广告销售额) / sum(广告花费)),2) ROI,
                  ROUND((sum(广告订单量)/sum(广告Click)),2) CR,
                  '' as '广告接手人'
                  FROM lazada_ad.base_data  where  广告类型 <> '联盟'   and date_format(业绩年月, '%Y%m')  = '{ad_date}' group by 业绩年月
              union all
                SELECT 'CPC' 广告类型,业绩年月,sum(广告花费) 广告花费,concat(round(sum(广告花费)/sum(广告销售额)*100,2),'%') acos,sum(广告销售额) 广告销售额,sum(站点销售额)站点销售额,
                  concat(round(sum(广告花费)/sum(站点销售额)*100,2),'%') '广告花费/站点销售额',concat(round(sum(广告销售额)/sum(站点销售额)*100,2),'%') '广告销售额/站点销售额',
                  sum(站点实际利润) 站点实际利润,sum(非广告部分利润) 非广告部分利润,sum(广告利润) 广告利润,sum(广告Click) 广告Click,
                  ROUND((sum(广告花费) / sum(广告Click)),2) CPC,
                  ROUND((sum(广告销售额) / sum(广告花费)),2) ROI,
                  ROUND((sum(广告订单量)/sum(广告Click)),2) CR,
                  广告接手人 '广告接手人'
                  FROM lazada_ad.base_data  where  广告类型 <> '联盟'  and date_format(业绩年月, '%Y%m')  = '{ad_date}' group by 业绩年月,广告接手人 order by 广告接手人
                  ''')
            df = pd.DataFrame(columns=base.keys(), data=base)
            # if ad_date<202103:
            #     df=df[['站点销售额',]]
        else:
            base = db.session.execute(f'''
                   SELECT
                     *
                     FROM lazada_ad.base_data  where  广告类型  <> '联盟' and date_format(业绩年月, '%Y%m')  = '{ad_date}' and 广告接手人 = '{host_name}'
                    union all
                   SELECT '合计' 广告类型,'','','','',业绩年月 ,sum(广告花费) 广告花费,concat(round(sum(广告花费)/sum(广告销售额)*100,2),'%') acos,sum(广告销售额) 广告销售额,sum(站点销售额)站点销售额,
                    concat(round(sum(广告花费)/sum(站点销售额)*100,2),'%')  '广告花费/站点销售额','','',sum(站点实际利润) 站点实际利润,sum(非广告部分利润) 非广告部分利润,sum(广告利润) 广告利润,
                    concat(round(sum(广告利润)/sum(站点实际利润)*100,2),'%'),concat(round(sum(广告销售额)/sum(站点销售额)*100,2),'%'),sum(广告订单量),sum(广告Click) 广告Click,'','','','','','','',
                    广告接手人 '广告接手人',''
                    FROM lazada_ad.base_data  where  广告类型  <> '联盟' and date_format(业绩年月, '%Y%m')  = '{ad_date}' and 广告接手人 = '{host_name}'
                      ''')
            df = pd.DataFrame(columns=base.keys(), data=base)
            df = df.iloc[::-1]
    else:
        if not host_name:
            base = db.session.execute(f'''
          SELECT '合计' 广告类型,业绩年月,sum(广告花费) 广告花费,concat(round(sum(广告花费)/sum(广告销售额)*100,2),'%') acos,sum(广告销售额) 广告销售额,sum(站点销售额)站点销售额,
            concat(round(sum(广告花费)/sum(站点销售额)*100,2),'%') '广告花费/站点销售额',concat(round(sum(广告销售额)/sum(站点销售额)*100,2),'%') '广告销售额/站点销售额',
            sum(站点实际利润) 站点实际利润,sum(非广告部分利润) 非广告部分利润,sum(广告利润) 广告利润,sum(广告Click) 广告Click,
            ROUND((sum(广告花费) / sum(广告Click)),2) CPC,
            ROUND((sum(广告销售额) / sum(广告花费)),2) ROI,
            ROUND((sum(广告订单量)/sum(广告Click)),2) CR,
            '' as '广告接手人'
            FROM lazada_ad.base_data  where  广告类型 = '{ad_type}'   and date_format(业绩年月, '%Y%m')  = '{ad_date}' group by 业绩年月,广告类型
        union all
          SELECT 广告类型,业绩年月,sum(广告花费) 广告花费,concat(round(sum(广告花费)/sum(广告销售额)*100,2),'%') acos,sum(广告销售额) 广告销售额,sum(站点销售额)站点销售额,
            concat(round(sum(广告花费)/sum(站点销售额)*100,2),'%') '广告花费/站点销售额',concat(round(sum(广告销售额)/sum(站点销售额)*100,2),'%') '广告销售额/站点销售额',
            sum(站点实际利润) 站点实际利润,sum(非广告部分利润) 非广告部分利润,sum(广告利润) 广告利润,sum(广告Click) 广告Click,
            ROUND((sum(广告花费) / sum(广告Click)),2) CPC,
            ROUND((sum(广告销售额) / sum(广告花费)),2) ROI,
            ROUND((sum(广告订单量)/sum(广告Click)),2) CR,
            广告接手人 '广告接手人'
            FROM lazada_ad.base_data  where  广告类型 = '{ad_type}'   and date_format(业绩年月, '%Y%m')  = '{ad_date}' group by 业绩年月,广告类型,广告接手人 order by 广告接手人
            ''')
            df = pd.DataFrame(columns=base.keys(), data=base)
        else:
            base = db.session.execute(f'''
               SELECT
                 *
                 FROM lazada_ad.base_data  where  广告类型 = '{ad_type}'   and date_format(业绩年月, '%Y%m')  = '{ad_date}' and 广告接手人 = '{host_name}'
                union all
               SELECT '合计' 广告类型,'','','','',业绩年月 ,sum(广告花费) 广告花费,concat(round(sum(广告花费)/sum(广告销售额)*100,2),'%') acos,sum(广告销售额) 广告销售额,sum(站点销售额)站点销售额,
                concat(round(sum(广告花费)/sum(站点销售额)*100,2),'%')  '广告花费/站点销售额','','',sum(站点实际利润) 站点实际利润,sum(非广告部分利润) 非广告部分利润,sum(广告利润) 广告利润,
                concat(round(sum(广告利润)/sum(站点实际利润)*100,2),'%'),concat(round(sum(广告销售额)/sum(站点销售额)*100,2),'%'),sum(广告订单量),sum(广告Click) 广告Click,'','','','','','','',
                广告接手人 '广告接手人',''
                FROM lazada_ad.base_data  where  广告类型 = '{ad_type}' and date_format(业绩年月, '%Y%m')  = '{ad_date}' and 广告接手人 = '{host_name}'
                  ''')
            df = pd.DataFrame(columns=base.keys(), data=base)
            df = df.iloc[::-1]
    df.rename(columns={"实际总毛利对比(正值为毛利增加)": "实际总毛利对比"}, inplace=True)
    df['业绩年月'] = df['业绩年月'].map(lambda x: arrow.get(x).format('YYYY-MM'))
    df = df.fillna(value='nan').applymap(lambda x: x.strip('nan') if '.' not in str(x) or '%' in str(x) else (
        str(x).split('.')[0] if abs(float(x)) > 100 and '%' not in str(x) else x))
    return render_template('month_data.html', df=df, ad_type=ad_type, ad_date=ad_date)


@app.route('/search', methods=["GET", "POST"])
def search():
    # base = db.session.execute(f'''
    #   SELECT 广告类型,replace(substring(业绩年月,3,8),'-','') 业绩年月,sum(广告销售额) 广告销售额 FROM lazada_ad.base_data group by 广告类型,业绩年月 order by 广告类型,业绩年月
    #         ''')
    # df = pd.DataFrame(columns=base.keys(), data=base)
    # j = df.to_json(orient="values", force_ascii=False)
    # j = json.dumps(j)
    # return j
    info = request.values
    for k, v in info.items():
        print(k + ':' + v)
    host_name = info.get('host_name', '')
    limit = info.get('limit')  # 每页显示的条数
    offset = info.get('offset')  # 分片数，(页码-1)*limit，它表示一段数据的起点
    ad_type = info.get('ad_type', '直通车')
    ad_date = info.get('ad_date', mn)
    account = info.get('account')

    if not host_name:
        base = db.session.execute(f'''
      SELECT '合计' 广告类型,业绩年月,sum(广告花费) 广告花费,concat(round(sum(广告花费)/sum(广告销售额)*100,2),'%') acos,sum(广告销售额) 广告销售额,sum(站点销售额)站点销售额,
        concat(round(sum(广告花费)/sum(站点销售额)*100,2),'%') '广告花费/站点销售额',concat(round(sum(广告销售额)/sum(站点销售额)*100,2),'%') '广告销售额/站点销售额',
        sum(站点实际利润) 站点实际利润,sum(非广告部分利润) 非广告部分利润,sum(广告利润) 广告利润,
        ROUND((sum(广告花费) / sum(广告Click)),2) CPC,
        ROUND((sum(广告销售额) / sum(广告花费)),2) ROI,
        ROUND((sum(广告订单量)/sum(广告Click)),2) CR,
        '' as '广告接手人'
        FROM lazada_ad.base_data  where  广告类型 = '{ad_type}'   and date_format(业绩年月, '%Y%m')  = '{ad_date}' group by 业绩年月,广告类型
    union all
      SELECT 广告类型,业绩年月,sum(广告花费) 广告花费,concat(round(sum(广告花费)/sum(广告销售额)*100,2),'%') acos,sum(广告销售额) 广告销售额,sum(站点销售额)站点销售额,
        concat(round(sum(广告花费)/sum(站点销售额)*100,2),'%') '广告花费/站点销售额',concat(round(sum(广告销售额)/sum(站点销售额)*100,2),'%') '广告销售额/站点销售额',
        sum(站点实际利润) 站点实际利润,sum(非广告部分利润) 非广告部分利润,sum(广告利润) 广告利润,
        ROUND(广告花费 / 广告Click,2) CPC,    
        ROUND(广告销售额 / 广告花费,2) ROI,
        ROUND(广告订单量/广告Click,2) CR,
        广告接手人 '广告接手人'
        FROM lazada_ad.base_data  where  广告类型 = '{ad_type}'   and date_format(业绩年月, '%Y%m')  = '{ad_date}' group by 业绩年月,广告类型,广告接手人
        ''')
        df = pd.DataFrame(columns=base.keys(), data=base)
    else:
        base = db.session.execute(f'''  
           SELECT
             a.*,
            ROUND(广告花费 / 广告Click,2) CPC,    
            ROUND(广告销售额 / 广告花费,2) ROI,
            ROUND(广告订单量/广告Click,2) CR
             FROM lazada_ad.base_data a where  广告类型 = '{ad_type}'   and date_format(业绩年月, '%Y%m')  = '{ad_date}' and 广告接手人 = '{host_name}'
            union all
           SELECT '合计' 广告类型,'','','','',业绩年月 ,sum(广告花费) 广告花费,concat(round(sum(广告花费)/sum(广告销售额)*100,2),'%') acos,sum(广告销售额) 广告销售额,sum(站点销售额)站点销售额,
            concat(round(sum(广告花费)/sum(站点销售额)*100,2),'%')  '广告花费/站点销售额','','',sum(站点实际利润) 站点实际利润,sum(非广告部分利润) 非广告部分利润,sum(广告利润) 广告利润,
            concat(round(sum(广告利润)/sum(站点实际利润)*100,2),'%'),concat(round(sum(广告销售额)/sum(站点销售额)*100,2),'%'),sum(广告订单量),sum(广告Click) 广告Click,'','','','','','','',
            广告接手人 '广告接手人','',
            ROUND((sum(广告花费) / sum(广告Click)),2) CPC,
            ROUND((sum(广告销售额) / sum(广告花费)),2) ROI,
            ROUND((sum(广告订单量)/sum(广告Click)),2) CR
            FROM lazada_ad.base_data  where  广告类型 = '{ad_type}' and date_format(业绩年月, '%Y%m')  = '{ad_date}' and 广告接手人 = '{host_name}' 
              ''')
        # base = db.session.execute(f'''
        #        SELECT
        #          *
        #          FROM lazada_ad.base_data  where  广告类型 = '{ad_type}'   and date_format(业绩年月, '%Y%m')  = '{ad_date}' and 广告接手人 like '{host_name}'
        #         union all
        #        SELECT '合计' 广告类型,'','','','',业绩年月 ,sum(广告花费) 广告花费,concat(round(sum(广告花费)/sum(广告销售额)*100,2),'%') acos,sum(广告销售额) 广告销售额,sum(站点销售额)站点销售额,
        #         concat(round(sum(广告花费)/sum(站点销售额)*100,2),'%')  '广告花费/站点销售额','','',sum(站点实际利润) 站点实际利润,sum(非广告部分利润) 非广告部分利润,sum(广告利润) 广告利润,
        #         concat(round(sum(广告利润)/sum(站点实际利润)*100,2),'%'),concat(round(sum(广告销售额)/sum(站点销售额)*100,2),'%'),sum(广告订单量),sum(广告Click) 广告Click,'','','','','','','',
        #         广告接手人 '广告接手人',''
        #         FROM lazada_ad.base_data  where  广告类型 = '{ad_type}' and date_format(业绩年月, '%Y%m')  = '{ad_date}' and 广告接手人 like '{host_name}'
        #           ''')
        df = pd.DataFrame(columns=base.keys(), data=base)
        df = df.iloc[::-1]
    df.rename(columns={"实际总毛利对比(正值为毛利增加)": "实际总毛利对比"}, inplace=True)
    df['业绩年月'] = df['业绩年月'].map(lambda x: arrow.get(x).format('YYYY-MM'))
    df = df.fillna(value='nan').applymap(lambda x: x.strip('nan') if '.' not in str(x) or '%' in str(x) else (
        str(x).split('.')[0] if abs(float(x)) > 100 and '%' not in str(x) else x))
    data = df.to_dict(orient="records")
    return jsonify({'total': len(data), 'rows': data[int(offset):(int(offset) + int(limit))]})

@app.route('/extraction', methods=['GET', 'POST'])
def extraction():
    # form = Submit()
    # if form.validate_on_submit():
    #     return GetData()()
    # month = request.form.get('month')
    ad_date = request.form.get('month')
    print(ad_date)
    return GetData(ad_date)(ad_date)


from werkzeug.utils import secure_filename
@app.route('/uploader', methods = ['GET', 'POST'])
def uploader():
    li=[]
    user_path=os.path.join('D:\月度统计', g.user.realname+arrow.now().shift(months=-1).format("YYYYMM"))
    if request.method == 'POST':
      f = request.files['file']
      with zipfile.ZipFile(file=f, mode='r') as zip_file:
        zip_file.extractall(path=user_path)
      # zip_files(f,user_path)
      for root, folds, files in os.walk(user_path):
          for item in folds:
              if '-th' in item.lower() or '-ph' in item.lower() or '-my' in item.lower():
                  try:
                      read_file(user_path,item)
                  except:
                      li.append(item)
                      pass
      if len(li)!=0:
        return f'上传失败:{li}'
    return '上传成功'

if __name__ == '__main__':
    app.debug = True
    app.run('0.0.0.0', port=8003)

    # from gevent import monkey
    #
    # monkey.patch_all()  # 打上猴子补丁
    # from gevent import pywsgi
    #
    # server = pywsgi.WSGIServer(('0.0.0.0', 8003), app)
    # server.serve_forever()
