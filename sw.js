/* 大阪京都行程頁：離線快取。線上一律先抓新的（network-first），斷網才給手機裡的那份。 */
var C='kansai-trip-v1';
self.addEventListener('install',function(){self.skipWaiting()});
self.addEventListener('activate',function(e){e.waitUntil(self.clients.claim())});
function put(req,res){if(res&&res.ok&&res.type==='basic'){var c=res.clone();caches.open(C).then(function(k){k.put(req,c)})}return res}
self.addEventListener('fetch',function(e){
  var r=e.request;if(r.method!=='GET')return;
  var u=new URL(r.url);if(u.origin!==location.origin)return;
  var key=u.origin+u.pathname;   /* 忽略 ?t= 之類的參數，離線時才對得上 */
  e.respondWith(fetch(r).then(function(res){return put(key,res)}).catch(function(){
    return caches.match(key).then(function(m){return m||caches.match(r,{ignoreSearch:true})}).then(function(m){return m||Response.error()})}));
});
self.addEventListener('message',function(e){
  var d=e.data||{};if(d.type!=='warm')return;
  (d.urls||[]).forEach(function(p){var u=new URL(p,self.registration.scope);
    fetch(u.href,{cache:'no-store'}).then(function(res){put(u.origin+u.pathname,res)}).catch(function(){})});
});
