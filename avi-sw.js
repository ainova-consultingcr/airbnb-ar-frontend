self.addEventListener("push", event => {
  let payload = {title:"AVI · Alerta ASADA", body:"Se detectó una nueva anomalía crítica.", tag:"avi-asada-alert", url:"./?property=asada_demo"};
  try { payload = {...payload, ...event.data.json()}; } catch {}
  event.waitUntil(self.registration.showNotification(payload.title, {
    body:payload.body,
    tag:payload.tag,
    data:{url:payload.url},
    icon:"favicon.ico",
    requireInteraction:true,
  }));
});

self.addEventListener("notificationclick", event => {
  event.notification.close();
  const target = event.notification.data?.url || "./?property=asada_demo";
  event.waitUntil(clients.matchAll({type:"window", includeUncontrolled:true}).then(windows => {
    const existing = windows.find(client => client.url.startsWith(new URL(target, self.location.origin).origin));
    return existing ? existing.focus() : clients.openWindow(target);
  }));
});
