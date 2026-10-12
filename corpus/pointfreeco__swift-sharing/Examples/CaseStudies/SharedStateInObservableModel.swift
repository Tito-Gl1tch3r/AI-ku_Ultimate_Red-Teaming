import Sharing
import SwiftUI

@Observable
private class Model {
  @ObservationIgnored
  @Shared(.appStorage("count")) var count = 0
}

struct SharedStateInObservableModelView: SwiftUICaseStudy {
  let caseStudyTitle = "Shared state in @Observable model"
  let caseStudyNavigationTitle = "In @Observable"
  let readMe = """
    This case study demonstrates that one can use `@Shared(.appStorage)` (and really any kind of \
    `@Shared` value) in an `@Observable` model, and it will work as expected. This is in contrast \
    to `@AppStorage` and other SwiftUI property wrappers, which only work when used directly \
    in SwiftUI views.
    """

  @State private var model = Model()

  var body: some View {
    Text("\(model.count)")
    Button("Decrement") {
      model.$count.withLock { $0 -= 1 }
    }
    Button("Increment") {
      model.$count.withLock { $0 += 1 }
    }
  }
}

#Preview {
  NavigationStack {
    CaseStudyView {
      SharedStateInObservableModelView()
    }
  }
}
