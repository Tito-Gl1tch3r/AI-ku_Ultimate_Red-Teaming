import JavaScriptEventLoop
import JavaScriptKit
import Sharing
import SwiftNavigation

@main
@MainActor
struct App {
  static var tokens: Set<ObserveToken> = []

  static func main() {
    JavaScriptEventLoop.installGlobalExecutor()

    @Shared(.localStorage("count")) var count = 0

    let document = JSObject.global.document

    var readMe = document.createElement("p")
    readMe.innerText = """
      This page demonstrates how the @Shared property wrapper can be used to power and persist the \
      state of a SwiftWasm application via local browser storage. Try incrementing and \
      decrementing the counter, refreshing the page to see the count persist, and opening multiple \
      browser windows to the same URL to see each count automatically kept in sync with one another.
      """
    _ = document.body.appendChild(readMe)

    var countLabel = document.createElement("div")
    _ = document.body.appendChild(countLabel)

    var decrementButton = document.createElement("button")
    decrementButton.innerText = "−"
    decrementButton.onclick = .object(
      JSClosure { _ in
        $count.withLock { $0 -= 1 }
        return .undefined
      }
    )
    _ = document.body.appendChild(decrementButton)

    var incrementButton = document.createElement("button")
    incrementButton.innerText = "+"
    incrementButton.onclick = .object(
      JSClosure { _ in
        $count.withLock { $0 += 1 }
        return .undefined
      }
    )
    _ = document.body.appendChild(incrementButton)

    observe {
      countLabel.innerText = .string("Count: \(count)")
    }
    .store(in: &tokens)
  }
}
