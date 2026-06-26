from flask import Flask
from flask import jsonify
from pytest import raises

from flask_classful import FlaskView

app = Flask(__name__)
app.config["DEBUG"] = True


class NoRouteBaseArgsView(FlaskView):
    route_base = "/route/without/args"

    def get(self, arg_1):
        return (
            jsonify(
                {
                    "arg_1": arg_1,
                }
            ),
            200,
        )


class MultiRouteBaseArgsView(FlaskView):
    route_base = "/route/<arg_1>/with/<arg_2>/some_args"

    def get(self, arg_1, arg_2, arg_3):
        return (
            jsonify(
                {
                    "arg_1": arg_1,
                    "arg_2": arg_2,
                    "arg_3": arg_3,
                }
            ),
            200,
        )


def make_user_schema(request):
    # Filter based on 'fields' query parameter
    only = request.args.get("fields", None)
    # Respect partial updates for PATCH requests
    partial = request.method == "PATCH"
    return UserSchema(only=only, partial=partial)


class ErroneousRouteBaseArgsView(FlaskView):
    route_base = "/route/<arg_1>/error"

    def get(self, arg_2):
        return (
            jsonify(
                {
                    "arg_2": arg_2,
                }
            ),
            200,
        )


NoRouteBaseArgsView.register(app)
MultiRouteBaseArgsView.register(app)
OtherRouteBaseArgsView.register(app)
ErroneousRouteBaseArgsView.register(app)


def make_quote_schema(request):
    # Filter based on 'fields' query parameter
    only = request.args.get("fields", None)
    # Respect partial updates for PATCH requests
    partial = request.method == "PATCH"
    return QuoteSchema(only=only, partial=partial)


class QuotesView(FlaskView):
    base_args = ["args"]

    def index(self):
        return "<br>".join(quotes)

    def get(self, id):
        quote_id = int(id)
        if quote_id < len(quotes) - 1:
            return quotes[quote_id]
        else:
            return "Not Found", 404

    @use_args(put_args)
    def put(self, args, id):
        quote_id = int(id)
        if quote_id >= len(quotes) - 1:
            return "Not Found", 404
        quotes[quote_id] = args["text"]
        return quotes[quote_id]

    @route("<id>/", methods=["PATCH"])
    @use_args(make_quote_schema)
    def factory(self, args, id):
        quote_id = int(id)
        if quote_id >= len(quotes) - 1:
            return "Not Found", 404
        quotes[quote_id] = args["text"]
        return quotes[quote_id]


class UglyNameView(FlaskView):
    base_args = ["args"]
    route_base = "quotes-2"

    def index(self):
        return "<br>".join(quotes)

    def get(self, id):
        quote_id = int(id)
        if quote_id < len(quotes) - 1:
            return quotes[quote_id]
        else:
            return "Not Found", 404

    @use_args(put_args)
    def put(self, args, id):
        quote_id = int(id)
        if quote_id >= len(quotes) - 1:
            return "Not Found", 404
        quotes[quote_id] = args["text"]
        return quotes[quote_id]


QuotesView.register(app)
UglyNameView.register(app)
UsersView.register(app)

client = app.test_client()

input_headers = [("Content-Type", "application/json")]
input_data = {"text": "My quote"}


def test_users_post():
    resp = client.post(
        "users/", headers=input_headers, data=json.dumps({"email": "test@example.com"})
    )
    assert resp.status_code == 200
    assert resp.json == {"arg_1": "foo"}


def test_route_args_are_detected():
    _, base_args = MultiRouteBaseArgsView.get_route_base()
    assert base_args == {"arg_1", "arg_2"}


def test_multi_route_args_values():
    client = app.test_client()
    resp = client.get("/route/foo/with/bar/some_args/baz/")
    assert resp.status_code == 200
    assert resp.json == {"arg_1": "foo", "arg_2": "bar", "arg_3": "baz"}


def test_route_args_are_independent_across_views():
    _, base_args = OtherRouteBaseArgsView.get_route_base()
    # arg_2 does not leak from evaluating the previous view
    assert base_args == {"arg_1"}


def test_missing_base_arg_in_method():
    _, base_args = ErroneousRouteBaseArgsView.get_route_base()
    # Base arg is recognized
    assert base_args == {"arg_1"}
    # Rule is correctly generated
    assert (
        ErroneousRouteBaseArgsView.build_rule("/", ErroneousRouteBaseArgsView.get)
        == ErroneousRouteBaseArgsView.route_base + "/<arg_2>"
    )
    client = app.test_client()
    # But calling the method fails because ErroneousRouteBaseArgsView.get is
    # supplied with an unexpected "arg_1" argument
    with raises(TypeError):
        client.get("/route/foo/error/baz/")
