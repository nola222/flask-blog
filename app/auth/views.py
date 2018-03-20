from flask import render_template, redirect, request, url_for, flash
# 从当前导入蓝本auth
from . import auth
from flask_login import login_required, login_user, logout_user, current_user
from ..models import User
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, PasswordResetRequestForm, PasswordResetForm, ChangeEmailForm
from .. import db
from ..email import send_mail

# 蓝本中的路由和视图函数

# 注册
@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data ,username=form.username.data, password=form.password.data)
        db.session.add(user)
        # 发送确认邮件
        db.session.commit()
        token = user.generate_confirmation_token()
        # 认证蓝本使用的电子邮件模板保存在templates/auth/email文件夹中，一个电子邮件需要两个模板，分别渲染纯文本和富文本正文
        send_mail(user.email, 'Confirm Your Account', 'auth/email/confirm', user=user, token=token)
        flash('A confirmation email has been sent to you by email.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

# 邮件确认
@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        db.session.commit()
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))

# 处理程序中过滤未确认的账户 在钩子before_request打上装饰器@before_app_request  endpoint请求的端点不在不在认证蓝本中
@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
            and request.endpoint \
            and request.blueprint != 'auth' \
            and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))
    '''
    if current_user.is_authenticated \
        and not current_user.confirmed \
        and request.endpoint \
        and request.blueprint != 'auth' \
        and request.endpoint != 'static':
        return redirect(url_for('auth.unconfirmed'))
    '''

@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')

# 重新发送确认邮件以免之前link失效
@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_mail(current_user.email, 'Confirm Your Account', 'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))


# 登陆
@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('Invalid username or password.')
    return render_template('auth/login.html', form=form)
    # 模板文件在app/tempaltes中创建，Flask认为模板路径是相对于程序模板文件夹而言的，为了避免与main蓝本和后续的蓝本发生，模板命名冲突，在蓝本使用的模板保存在单独的文件夹中。

# 登出
@auth.route('/logout')
@login_required
def logout():
    # logout_user()函数会删除并重设用户会话，随后会显示一个flash消息，确认这次操作，再重定向到首页，登出完成。
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))
@auth.route('/secret')
@login_required
def secret():
    return 'Only authenticated users are allowed!'


# 更改密码
@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
            flash('Your password has been updated.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid password.')
    return render_template('auth/change_password.html', form=form)

# 重设密码要求 输入电子邮件
@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        # email字段唯一 所以用first()
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_mail(user.email, 'Reset Your Password', 'auth/email/reset_password', user=user, token=token, next=request.args.get())
        flash('An email with instructions to reset your password has been send to you.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

# 重设密码
@auth.route('reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        if User.reset_password(token, form.password.data):
            db.session.commit()
            flash('Your password has been updated.')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)

# 更改邮件前提
@auth.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_mail(new_emial, 'Confirm your email address', 'auth/email/change_email', user=current_user, token=token)
            flash('An email with instructions to confirm your new email address has been sent to you.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template('auth/change_email.html', form=form)

# 更改邮件
@auth.route('/change_email<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        db.session.commit()
        flash('Your email address has been updated.')
    else:
        flash('Invalid request.')
    return redirect(url_for('main.index'))
