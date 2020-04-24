import frappe
import jwt
from frappe.auth import HTTPRequest, LoginManager, get_lang_code, check_session_stopped, CookieManager
from frappe import _


# frappe's CookieManager is having old class style
class CookieManagerJWT(CookieManager, object):
	def flush_cookies(self, response):
		# use this opportunity to set the response headers
		response.headers["X-Client-Site"] = frappe.local.site
		if frappe.flags.jwt_clear_cookies:
			# Case when right after login
			# We set the flag on session_create
			self.cookies = frappe._dict()
		if frappe.flags.jwt:
			# Case when the incoming request has jwt token
			# We leave cookies untouched
			# There can be other browser tabs
			return
		return super(CookieManagerJWT, self).flush_cookies(response)


class RenovationHTTPRequest(HTTPRequest):
	def __init__(self):
		# Get Environment variables
		self.domain = frappe.request.host
		if self.domain and self.domain.startswith('www.'):
			self.domain = self.domain[4:]

		if frappe.get_request_header('X-Forwarded-For'):
			frappe.local.request_ip = (frappe.get_request_header(
				'X-Forwarded-For').split(",")[0]).strip()

		elif frappe.get_request_header('REMOTE_ADDR'):
			frappe.local.request_ip = frappe.get_request_header('REMOTE_ADDR')

		else:
			frappe.local.request_ip = '127.0.0.1'

		# language
		self.set_lang()
	
		# set db before jwt check, so token error handling can be stored
		# We get Internal Server Error otherwise
		self.connect()

		# JWT
		jwt_token = None
		# Check for Auth Header, if present, replace the request cookie value
		if frappe.get_request_header("Authorization"):
			token_header = frappe.get_request_header(
				"Authorization").split(" ")
			
			if token_header[0].lower() not in ("basic", "bearer") and ":" not in token_header[-1]:
				jwt_token = token_header[-1]
		elif frappe.request.path.startswith('/private/files/') and frappe.request.args.get("token"):
			jwt_token = frappe.request.args.get("token")

		if jwt_token:
			frappe.flags.jwt = jwt_token
			token_info = jwt.decode(jwt_token, frappe.utils.password.get_encryption_key())

			# Not checking by IP since it could change on network change (Wifi -> Mobile Network)
			# if token_info.get('ip') != frappe.local.request_ip:
			# 	frappe.throw(frappe._("Invalide IP", frappe.AuthenticationError))

			# werkzueg cookies structure is immutable
			frappe.request.cookies = frappe._dict(frappe.request.cookies)
			frappe.request.cookies['sid'] = token_info.get('sid')


		# load cookies
		frappe.local.cookie_manager = CookieManagerJWT()

		# login
		frappe.local.login_manager = LoginManager()

		if frappe.form_dict._lang:
			lang = get_lang_code(frappe.form_dict._lang)
			if lang:
				frappe.local.lang = lang

		self.validate_csrf_token()

		# write out latest cookies
		frappe.local.cookie_manager.init_cookies()

		# check status
		check_session_stopped()


def make_jwt(user, expire_on=None, secret=None):
	if not frappe.session.get('sid') or frappe.session.sid == "Guest":
		return
	if not secret:
		secret = frappe.utils.password.get_encryption_key()
	if expire_on and not isinstance(expire_on, frappe.utils.datetime.datetime):
		expire_on = frappe.utils.get_datetime(expire_on)

	id_token_header = {
		"typ": "jwt",
		"alg": "HS256"
	}
	id_token = {
		"sub": user,
		"ip": frappe.local.request_ip,
		"sid": frappe.session.get('sid')
	}
	if expire_on:
		id_token['exp'] = int((expire_on - frappe.utils.datetime.datetime(1970, 1, 1)).total_seconds())
	token_encoded = jwt.encode(id_token, secret, algorithm='HS256', headers=id_token_header).decode("ascii")
	frappe.flags.jwt = token_encoded
	return token_encoded