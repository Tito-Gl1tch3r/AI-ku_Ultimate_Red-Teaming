import Sharing
import SwiftUI

struct InMemorySharedStateView: SwiftUICaseStudy {
  let caseStudyTitle = "@Shared(.inMemory)"
  let readMe = """
    This case study demonstrates how to use the built-in `inMemory` strategy to share state \
    globally (and safely) with the entire app, but its contents will be cleared out when the \
    app is restarted.

    Note that `@Shared(.inMemory)` differs from `@State` in that `@State` will be cleared out \
    when navigating away from this view and coming back. Whereas the `@Shared` value is persisted \
    globally for the entire lifetime of the app.
    """

  @Shared(.inMemory("count")) var sharedCount = 0
  @State var stateCount = 0

  var body: some View {
    Section {
      Text("\(stateCount)")
      Button("Increment") {
        stateCount += 1
      }
      Button("Decrement") {
        stateCount -= 1
      }
    } header: {
      Text("@State")
    }

    Section {
      Text("\(sharedCount)")
      Button("Increment") {
        $sharedCount.withLock { $0 += 1 }
      }
      Button("Decrement") {
        $sharedCount.withLock { $0 -= 1 }
      }
    } header: {
      Text("@Shared(.inMemory)")
    }
  }
}

#Preview {
  NavigationStack {
    CaseStudyView {
      InMemorySharedStateView()
    }
  }
}
