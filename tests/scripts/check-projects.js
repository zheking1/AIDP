const http = require('http');

function get(path) {
  return new Promise((resolve, reject) => {
    const req = http.get(`http://192.168.0.100:8883${path}`, {
      headers: { 'Cookie': 'session=admin-session-token' }
    }, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve({ status: res.statusCode, body: d }));
    });
    req.on('error', reject);
  });
}

(async () => {
  // Login first
  const loginRes = await new Promise((resolve, reject) => {
    const data = 'username=admin&password=admin123';
    const req = http.request('http://192.168.0.100:8883/api/auth/login/form', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': Buffer.byteLength(data) }
    }, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: d }));
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
  
  const cookies = loginRes.headers['set-cookie'];
  const cookieStr = cookies ? cookies.map(c => c.split(';')[0]).join('; ') : '';
  console.log('Login cookies:', cookieStr);

  // Get projects
  const projRes = await new Promise((resolve, reject) => {
    const req = http.get('http://192.168.0.100:8883/api/projects', {
      headers: { 'Cookie': cookieStr }
    }, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve({ status: res.statusCode, body: d }));
    });
    req.on('error', reject);
  });
  console.log('Projects API:', projRes.status, projRes.body.substring(0, 500));
})();
