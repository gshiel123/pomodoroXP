import Foundation

enum TelegramError: LocalizedError {
    case notConfigured
    case api(String)

    var errorDescription: String? {
        switch self {
        case .notConfigured:
            return "Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to \(Telegram.envPath)"
        case .api(let message):
            return message
        }
    }
}

enum Telegram {
    // build.sh records the project folder in Info.plist so the .env stays inside it.
    static let envPath: String = {
        let dir = Bundle.main.object(forInfoDictionaryKey: "PomodoroProjectDir") as? String
            ?? FileManager.default.currentDirectoryPath
        return (dir as NSString).appendingPathComponent(".env")
    }()

    // Re-read on every send so edits to the .env apply without restarting the app.
    private static func loadEnv() -> [String: String] {
        guard let text = try? String(contentsOfFile: envPath, encoding: .utf8) else { return [:] }
        var values: [String: String] = [:]
        for rawLine in text.split(whereSeparator: \.isNewline) {
            let line = rawLine.trimmingCharacters(in: .whitespaces)
            guard !line.hasPrefix("#"), let eq = line.firstIndex(of: "=") else { continue }
            let key = line[..<eq].trimmingCharacters(in: .whitespaces)
            let value = line[line.index(after: eq)...]
                .trimmingCharacters(in: .whitespaces)
                .trimmingCharacters(in: CharacterSet(charactersIn: "\"'"))
            values[key] = value
        }
        return values
    }

    static func send(_ text: String, completion: ((Error?) -> Void)? = nil) {
        let env = loadEnv()
        guard let token = env["TELEGRAM_BOT_TOKEN"], !token.isEmpty,
              let chatID = env["TELEGRAM_CHAT_ID"], !chatID.isEmpty,
              let url = URL(string: "https://api.telegram.org/bot\(token)/sendMessage")
        else {
            completion?(TelegramError.notConfigured)
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["chat_id": chatID, "text": text])
        request.timeoutInterval = 15

        URLSession.shared.dataTask(with: request) { data, _, error in
            var result: Error? = error
            if error == nil,
               let data,
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               json["ok"] as? Bool != true {
                result = TelegramError.api(json["description"] as? String ?? "Telegram rejected the message")
            }
            DispatchQueue.main.async { completion?(result) }
        }.resume()
    }
}
