import AppKit
import UserNotifications

enum Session {
    case work
    case rest
}

struct Preset {
    let work: Int
    let rest: Int
    var label: String { "\(work) / \(rest) minutes" }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private let presets = [Preset(work: 25, rest: 5), Preset(work: 50, rest: 10)]
    private let presetKey = "presetIndex"

    private var statusItem: NSStatusItem!
    private var startPauseItem: NSMenuItem!
    private var skipItem: NSMenuItem!
    private var presetItems: [NSMenuItem] = []

    private var timer: Timer?
    private var presetIndex = 0
    private var session: Session = .work
    private var endDate: Date?
    private var remaining: TimeInterval = 0

    private var preset: Preset { presets[presetIndex] }
    private var isRunning: Bool { endDate != nil }

    func applicationDidFinishLaunching(_ notification: Notification) {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }

        presetIndex = min(UserDefaults.standard.integer(forKey: presetKey), presets.count - 1)
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.button?.font = NSFont.monospacedDigitSystemFont(ofSize: NSFont.systemFontSize, weight: .regular)
        buildMenu()
        reset()
    }

    private func buildMenu() {
        let menu = NSMenu()

        startPauseItem = addItem(to: menu, "Start", #selector(toggleStartPause), key: "s")
        skipItem = addItem(to: menu, "Skip to Break", #selector(skip), key: "")
        addItem(to: menu, "Reset", #selector(resetClicked), key: "r")
        menu.addItem(.separator())

        for (i, p) in presets.enumerated() {
            let item = addItem(to: menu, p.label, #selector(selectPreset(_:)), key: "\(i + 1)")
            item.tag = i
            presetItems.append(item)
        }
        menu.addItem(.separator())
        addItem(to: menu, "Send Test Telegram Message", #selector(sendTestTelegram), key: "")
        addItem(to: menu, "Quit Pomodoro", #selector(quit), key: "q")

        statusItem.menu = menu
    }

    @discardableResult
    private func addItem(to menu: NSMenu, _ title: String, _ action: Selector, key: String) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
        item.target = self
        menu.addItem(item)
        return item
    }

    // MARK: - Actions

    @objc private func toggleStartPause() {
        isRunning ? pause() : start()
    }

    @objc private func skip() {
        finishSession(notify: false)
    }

    @objc private func resetClicked() {
        reset()
    }

    @objc private func selectPreset(_ sender: NSMenuItem) {
        presetIndex = sender.tag
        UserDefaults.standard.set(presetIndex, forKey: presetKey)
        reset()
    }

    @objc private func sendTestTelegram() {
        Telegram.send("🍅 Test from Pomodoro: Telegram alerts are working.") { [weak self] error in
            if let error {
                self?.showLocalNotification(title: "Telegram test failed", body: error.localizedDescription)
            } else {
                self?.showLocalNotification(title: "Telegram test sent", body: "Check your Telegram chat.")
            }
        }
    }

    @objc private func quit() {
        NSApp.terminate(nil)
    }

    // MARK: - Timer

    private func start() {
        endDate = Date().addingTimeInterval(remaining)
        timer?.invalidate()
        let t = Timer(timeInterval: 0.5, repeats: true) { [weak self] _ in self?.tick() }
        RunLoop.main.add(t, forMode: .common)
        timer = t
        refresh()
    }

    private func pause() {
        if let endDate { remaining = max(0, endDate.timeIntervalSinceNow) }
        stopTimer()
        refresh()
    }

    private func reset() {
        stopTimer()
        session = .work
        remaining = TimeInterval(preset.work * 60)
        refresh()
    }

    private func stopTimer() {
        timer?.invalidate()
        timer = nil
        endDate = nil
    }

    private func tick() {
        guard let endDate else { return }
        remaining = max(0, endDate.timeIntervalSinceNow)
        if remaining <= 0 {
            finishSession(notify: true)
        } else {
            refresh()
        }
    }

    private func finishSession(notify: Bool) {
        let wasRunning = isRunning
        let finishedWork = session == .work
        session = finishedWork ? .rest : .work
        remaining = TimeInterval((finishedWork ? preset.rest : preset.work) * 60)

        if notify {
            sendNotification(
                title: finishedWork ? "Break time" : "Back to work",
                body: finishedWork ? "Take a \(preset.rest)-minute break." : "Focus for \(preset.work) minutes."
            )
        }

        stopTimer()
        if wasRunning { start() } else { refresh() }
    }

    // MARK: - UI

    private func refresh() {
        let secs = Int(remaining.rounded(.up))
        let icon = session == .work ? "🍅" : "☕️"
        statusItem.button?.title = String(format: "%@ %02d:%02d", icon, secs / 60, secs % 60)
        statusItem.button?.appearsDisabled = !isRunning

        startPauseItem.title = isRunning ? "Pause" : "Start"
        skipItem.title = session == .work ? "Skip to Break" : "Skip Break"
        for item in presetItems {
            item.state = item.tag == presetIndex ? .on : .off
        }
    }

    private func sendNotification(title: String, body: String) {
        NSSound(named: "Glass")?.play()
        showLocalNotification(title: title, body: body)
        Telegram.send("\(session == .work ? "🍅" : "☕️") \(title): \(body)")
    }

    private func showLocalNotification(title: String, body: String) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
