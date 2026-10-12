import Sharing
import SwiftUI

struct AppStorageStateView: SwiftUICaseStudy {
  let caseStudyTitle = "@Shared(.appStorage)"
  let readMe = """
    Demonstrates how to use `appStorage` persistence strategy to persist simple pieces of data \
    to user defaults. This tool works when installed directly in a SwiftUI view, just like \
    `@AppStorage`, but most importantly it still works when installed in othe parts of your app, \
    including `@Observable` models, UIKit view controllers, and more.
    """

  @State private var model = Model()

  var body: some View {
    Section {
      Text("\(model.count)")
      Button("Decrement") {
        model.$count.withLock { $0 -= 1 }
      }
      Button("Increment") {
        model.$count.withLock { $0 += 1 }
      }
    }
  }
}

@Observable
private class Model {
  @ObservationIgnored
  @Shared(.appStorage("count")) var count = 0
}

#Preview {
  NavigationStack {
    CaseStudyView {
      AppStorageStateView()
    }
  }
}
