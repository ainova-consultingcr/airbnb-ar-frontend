self.addEventListener("notificationclick", event => {
  event.notification.close();
  const target = event.notification.data?.url || "./?property=asada_demo";
  event.waitUntil(clients.matchAll({type:"window", includeUncontrolled:true}).then(windows => {
    const existing = windows.find(client => client.url.startsWith(new URL(target, self.location.origin).origin));
    return existing ? existing.focus() : clients.openWindow(target);
  }));
});
