/* Live diagnostics use the player's existing GPIO reader. Potentiometers stay manual. */
function motionDiagnosticsHTML() {
  return `<section class="motion-diagnostics" id="motion-diagnostics" aria-label="Bewegungssensor live prüfen">
    <h3>Sensor live prüfen</h3>
    <p class="help">Sensorsignal, Nachlaufzeit und Bildschirmstatus direkt vom Pi. Der Start kann bis zum nächsten Abgleich dauern (normalerweise 15 Sekunden), danach kommen Messwerte etwa jede Sekunde.</p>
    <div class="motion-actions"><button type="button" id="motion-live-toggle">Live-Diagnose starten</button><button type="submit" class="small">Einstellungen übernehmen</button></div>
    <p class="help">Änderungen oben erst übernehmen. Bei laufender Diagnose bleibt dieses Fenster zum Einstellen geöffnet.</p>
    <p id="motion-live-status" role="status">Diagnose noch nicht gestartet.</p>
    <div id="motion-live-data"></div>
    <details class="motion-guide"><summary>Potis einstellen &amp; Fehler eingrenzen</summary>
      <ol><li>Sensorfunktion oben aktivieren, zum Testen 1 Minute Nachlaufzeit wählen und Einstellungen übernehmen.</li>
      <li>Jumper am HC-SR501 auf H stellen. TIME möglichst kurz, SENS zunächst mittig einstellen. Zuordnung und Drehrichtung anhand der Anleitung deiner Platine prüfen.</li>
      <li>Einlaufzeit abwarten. Im gewünschten Bereich gehen: Das Signal muss auf HIGH wechseln. Empfindlichkeit und Sensorposition anpassen.</li>
      <li>Bereich verlassen: Erst muss LOW erscheinen, dann zählt die Software-Nachlaufzeit herunter. Anschließend Bildschirm und Beleuchtung vor Ort kontrollieren.</li>
      <li>Bleibt HIGH bestehen, kommen weitere Auslösungen oder eine lange Hardware-Haltezeit infrage. Bei dauerhaft LOW Anschluss an GPIO17 (physischer Pin 11), Versorgung, Position und Empfindlichkeit prüfen.</li></ol>
      <p class="help">HIGH kann eine gehaltene Meldung sein; LOW beweist weder einen leeren Raum noch einen intakten Anschluss. Ein PIR erkennt still sitzende Personen nicht zuverlässig. Die Potistellungen sind nicht per Software auslesbar. Signalphasen sind keine Personenzählung und messen die Hardware-Haltezeit bei wiederholten Auslösungen nicht eindeutig.</p>
    </details>
  </section>`;
}

function motionDuration(value) {
  if (value == null) return "–";
  const seconds = Math.max(0, Math.ceil(value));
  return seconds < 60 ? `${seconds} s` : `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
}

function motionDiagnosticView(result) {
  const sample = result.sample;
  if (!sample) {
    return `<p class="help">Noch keine Messwerte. Letzter Geräteabgleich: ${e(date(result.last_seen))}. Falls nach 30 Sekunden nichts erscheint: Verbindung prüfen und sicherstellen, dass NAS und Pi-Player den neuen Softwarestand verwenden.</p>${result.reported?.error ? `<p class="form-error">Letzter gemeldeter Fehler: ${e(result.reported.error)}</p>` : ""}`;
  }
  const stale = result.age_seconds > 5;
  const signal = sample.signal === null ? "Unbekannt" : sample.signal ? "HIGH · Signal aktiv" : "LOW · Signal inaktiv";
  const phases = {
    disabled: "Sensorfunktion am Pi ausgeschaltet. Innerhalb der Betriebszeiten bleibt das Bild aktiv.",
    error: `Sensor nicht lesbar. Die Anzeige bleibt innerhalb der Betriebszeiten aktiv. Neuer Leseversuch in ${motionDuration(sample.retry_seconds)}.`,
    warmup: `Sensor läuft ein: noch ${motionDuration(sample.warmup_seconds)}. Danach beginnt die Nachlaufzeit.`,
    urgent: "Eine Sofortmeldung hält die Anzeige aktiv. Nach ihrem Ende beginnt die Nachlaufzeit erneut.",
    high: "Das aktive Sensorsignal verlängert die Nachlaufzeit laufend. Erst nach LOW kann sie ablaufen.",
    hold: "Das Sensorsignal ist inaktiv. Die Software-Nachlaufzeit läuft.",
    idle: "Die Nachlaufzeit ist abgelaufen. Der Player fordert die gewählte Abschaltung an.",
  };
  const output = { on: "Bildsignal an", standby: "HDMI abgeschaltet", black: "Schwarzbild · Beleuchtung kann anbleiben" };
  const pending = ["enabled", "idle_minutes", "power_mode"].some(
    (key) => sample[key] !== (result.settings[key] ?? defaults.motion[key]),
  );
  const countdown = ["high", "warmup", "urgent"].includes(sample.phase)
    ? "Wird noch nicht heruntergezählt"
    : sample.phase === "hold" || sample.phase === "idle" ? motionDuration(sample.remaining_seconds) : "–";
  const items = [
    ["Sensorsignal · GPIO17 / Pin 11", signal],
    ["Aktuelle Signalphase beobachtet seit", motionDuration(sample.signal_seconds)],
    ["Software-Nachlaufzeit verbleibend", countdown],
    ["Vom Player gemeldete Ausgabe", output[sample.display]],
  ];
  return `${stale ? '<p class="motion-warning">Keine aktuellen Messwerte – folgende Werte sind veraltet. Verbindung und Player prüfen.</p>' : ""}
    ${pending ? '<p class="motion-warning">Gespeicherte Einstellungen sind am Pi noch nicht angekommen.</p>' : ""}
    <div class="motion-signal ${stale || sample.signal === null ? "unknown" : sample.signal ? "high" : "low"}">${e(signal)}</div>
    <p class="motion-explanation">${e(phases[sample.phase])}</p>
    <dl class="motion-values">${items.map(([label, value]) => `<div><dt>${e(label)}</dt><dd>${e(value)}</dd></div>`).join("")}</dl>
    <p class="help">Am Pi: Sensor ${sample.enabled ? "ein" : "aus"} · Nachlaufzeit ${sample.idle_minutes} min · ${sample.power_mode === "hdmi" ? "HDMI-Abschaltung" : "Schwarzbild"}.<br>Anzeigeentscheidung: ${e(sample.reason)}.<br>Alter des Messwerts: ${motionDuration(result.age_seconds)}. Die Ausgabe ist eine Softwaremeldung, keine Messung der Monitorbeleuchtung.</p>
    ${sample.sensor_error ? `<p class="form-error">${e(sample.sensor_error)}</p>` : ""}
    ${sample.display_error ? `<p class="form-error">${e(sample.display_error)}</p>` : ""}
    <h4>Letzte Signalwechsel</h4>
    <p class="help">Bis zu 20 Beobachtungen seit Aktivierung oder Playerstart. Eine Erstbeobachtung ist kein nachgewiesener Signalwechsel; während der Einlaufzeit sind Auslösungen noch nicht aussagekräftig.</p>
    <ol class="motion-events">${sample.events.map((event) => `<li><strong>${event.signal ? "HIGH" : "LOW"}</strong> · vor ${motionDuration(event.ago_seconds)}${event.initial ? " · Erstbeobachtung" : ` · vorher ${event.signal ? "LOW" : "HIGH"} für ${motionDuration(event.previous_seconds)}`}</li>`).join("") || "<li>Noch keine Signalbeobachtung.</li>"}</ol>`;
}

function initMotionDiagnostics(id) {
  const root = $("#motion-diagnostics"), button = $("#motion-live-toggle", root);
  const status = $("#motion-live-status", root), data = $("#motion-live-data", root);
  let running = false, generation = 0, timer, freshnessTimer, renewAt = 0, lastResult, receivedAt;
  function render(result) {
    const scrollTop = $(".motion-events", data)?.scrollTop || 0;
    data.innerHTML = motionDiagnosticView(result);
    const events = $(".motion-events", data);
    if (events) events.scrollTop = scrollTop;
  }
  const stop = () => {
    running = false;
    generation++;
    clearTimeout(timer);
    clearInterval(freshnessTimer);
    root.dataset.running = "false";
    button.textContent = "Live-Diagnose starten";
    status.textContent = "Diagnose beendet. Die schnelle Übertragung endet spätestens nach 30 Sekunden.";
    data.innerHTML = "";
  };
  async function poll(current) {
    if (!running || current !== generation || !root.isConnected) return;
    try {
      const renew = Date.now() >= renewAt;
      const result = await api(`/admin/devices/${id}/motion`, renew ? "POST" : "GET");
      if (!running || current !== generation || !root.isConnected) return;
      if (renew) renewAt = Date.now() + 10000;
      lastResult = result;
      receivedAt = Date.now();
      status.textContent = !result.sample ? "Warte auf Messwerte vom Pi …"
        : result.age_seconds > 5 ? "Messwerte veraltet" : "Live-Diagnose läuft";
      render(result);
    } catch (error) {
      if (!running || current !== generation || !root.isConnected) return;
      status.textContent = `Live-Verbindung unterbrochen: ${error.message}`;
      if (lastResult?.sample) {
        render({
          ...lastResult,
          age_seconds: Math.max(6, lastResult.age_seconds + (Date.now() - receivedAt) / 1000),
        });
      }
    }
    if (running && current === generation && root.isConnected) timer = setTimeout(() => poll(current), 1000);
  }
  button.onclick = () => {
    if (running) return stop();
    running = true;
    root.dataset.running = "true";
    button.textContent = "Live-Diagnose beenden";
    renewAt = 0;
    lastResult = null;
    status.textContent = "Live-Diagnose wird gestartet …";
    // A hanging fetch must not leave the last packet labelled live indefinitely.
    freshnessTimer = setInterval(() => {
      if (!running || !lastResult?.sample) return;
      const age = lastResult.age_seconds + (Date.now() - receivedAt) / 1000;
      if (age > 5) {
        status.textContent = "Messwerte veraltet – warte auf neue Rückmeldung";
        render({ ...lastResult, age_seconds: age });
      }
    }, 1000);
    poll(++generation);
  };
  return stop;
}
