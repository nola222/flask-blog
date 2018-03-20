# from_json要是没有数据会抛异常ValidationError 把错误交给调用者ValueError
class ValidationError(ValueError):
    pass
