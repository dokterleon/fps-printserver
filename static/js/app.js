async function loadStatus(){
  const res = await fetch('/api/status');
  const d = await res.json();

  document.getElementById('state').innerText = d.state;
  document.getElementById('printer').innerText = d.printer;
  document.getElementById('media').innerText = d.media;
  document.getElementById('remaining').innerText =
    (d.remaining || '').replace(' native prints remaining on 6x4 (PC) media','');
  document.getElementById('mode').innerText = d.mode;
  document.getElementById('queue').innerText = d.queue;
}
loadStatus();
setInterval(loadStatus, 2000);
