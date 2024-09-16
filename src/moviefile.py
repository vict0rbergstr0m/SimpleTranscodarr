#!DEPRECATED
# class Moviefile:
#     def __init__(self, name: str, path: str, res: str, encoding: str, container: str, size: str) -> None:
#         self.name = name;
#         self.path = path;
#         self.res = res;
#         self.encoding = encoding;
#         self.container = container;
#         self.size = f"{size/ (1024 * 1024 * 1024):.2f}GB";
        

# import json

# class MovieFileEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, Moviefile):
#             return {
#                 "name": obj.name,
#                 "path": obj.path,
#                 "res": obj.res,
#                 "encoding": obj.encoding,
#                 "container": obj.container,
#                 "size": obj.size
#             }
#         return super().default(obj)