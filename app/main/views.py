from datetime import datetime
from flask import render_template, session, redirect, url_for, abort, flash, request, current_app, make_response
from . import main
from .forms import NameForm, EditProfileForm, EditProfileAdminForm, PostForm, CommentForm
from .. import db
from ..models import User, Role, Post, Permission, Comment
from flask_login import login_required, current_user
from ..decorators import admin_required, permission_required

@main.route('/', methods=['GET', 'POST'])
def index():
    form = PostForm()
    if current_user.can(Permission.WRITE) and \
        form.validate_on_submit():
        # _get_current_object() 调用此函数获取数据库真正的用户对象，current_user是由flask_login提供的一个轻度包装的代理对象。
        post = Post(body=form.body.data, author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('.index'))
    # request.args - 获取渲染的页数，默认是渲染一页
    page = request.args.get('page', 1, type=int)
    # 按照时间戳降序   实现分页 query时为了渲染指定页数 使用paginate替换all() error_out为True时超出返回404  为False超出返回空列表 首页展示有限 若想查看第二页url上加上?page=2  restful风格的url
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
                 page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
                 error_out=False)
    # paginate()方法返回一个Pagination对象 属性items表示当前页面中的记录
    posts = pagination.items 
    return render_template('index.html', form=form, posts=posts, show_followed=show_followed, pagination=pagination)
    '''
    name = None
    age = None
    gender = None
    form = NameForm()

    if form.validate_on_submit():
        session['name'] = form.name.data
        session['age'] = form.age.data
        session['gender'] = form.gender.data
       
        #利用session保存变量只要secret_key不变，重定向就不需要自己手动设置为空>串
        form.name.data = ''
        form.age.data = ''
        form.gender.data = ''
        
        # 本可简单写成redirect('/') 但一般使用flask提供的url生成函数url_for()>，因为其使用url映射生成url，保证url和定义的路由兼容
        return redirect(url_for('.index'))
    # session.get('name')用法同字典，get()如果键不存在，默认返回None
    return render_template('index.html', form=form, name=session.get('name'), age=session.get('age'), gender=session.get('gender'), known=session.get('known', False), current_time=datetime.utcnow())
    #return render_template('index.html',current_time=datetime.utcnow())
    '''
        #...
        # 在蓝本中，flask会为蓝本中的全部端点加上一个命名空间，在不同的蓝本中使用相同的端点名，而不会产生冲突。所以视图函数注册的端点名是main.index,url_for(main.index),简略写法如下，可省略蓝本名。说明同一蓝本中的重定向可以使用简写，跨蓝本的必须带上蓝本名。

# 使用蓝本两个不同点
# 1.--- 与前面错误处理程序一样，路由修饰器由蓝本提供
# 2.--- url_for()函数的用法不同 之前url_for()第一个参数是路由的端点名，  在程序中默认为视图函数的名字，在单脚本程序中，index()函数的url使用url_for('index')获取

# 表单对象也要移动到蓝本中


# 普通用户资料页面的路由
@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template('user.html', user=user, posts=posts)

# 普通用户资料编辑路由
@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)
    
       
# 管理员资料的路由
@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)

# 文章固定链接 每篇文章使用唯一一个url引用
@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    # 支持博客文章评论
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        print('+++++++++++++++',comment)
        db.session.add(comment)
        db.session.commit()   
        flash('Your comment has been published.')
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    # page=-1用于请求评论的最后一页
    if page == -1:
        page = (post.comments.count() - 1) // \
            current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    # post模板接受一个列表作为参数，列表就是要渲染的文章
    return render_template('post.html', posts=[post], form=form,
                            comments=comments, pagination=pagination)


# 编辑博客文章的路由
@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
        not current_user.can(Permission.ADMIN):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash('The post has been updated.')
        return redirect(url_for('.post', id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html', form=form)

# 关注路由和视图
@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are now following %s.' %username)
    return redirect(url_for('.user', username=username))

# 不关注
@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following %s anymore.' %username)
    return redirect(url_for('.user', username=username))

# 关注者
@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    # 分页
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)
# 被关注者
@main.route('/followed_by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    # 分页
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)


# 查询所有文章还是所关注用户的文章
@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    return resp
    

# 管理评论的路由
@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments,
                           pagination=pagination, page=page)

# 启用显示评论路由
@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.moderate', page=request.args.get('page', 1, type=int)))

# 禁用显示评论路由
@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.moderate', page=request.args.get('page', 1, type=int)))

