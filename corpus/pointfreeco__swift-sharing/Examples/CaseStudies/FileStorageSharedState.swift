import Dependencies
import Sharing
import SwiftUI

struct Timestamp: Codable, Identifiable {
  let id: UUID
  var value: Date
}

struct FileStorageSharedState: SwiftUICaseStudy {
  let caseStudyTitle = "@Share(.fileStorage)"
  let readMe = """
    This case study demonstrates how to use the built-in `fileStorage` strategy to persist data
    to the file system. Changes made to the `timestamps` state is automatically saved to disk,
    and if the file on disk ever changes its contents will be loaded into the `timestamps` state
    automatically.
    """

  @Shared(.fileStorage(.documentsDirectory.appending(component: "timestamps.json")))
  var timestamps: [Timestamp] = []

  var body: some View {
    Section {
      Button("Clear") {
        withAnimation {
          $timestamps.withLock { $0 = [] }
        }
      }
    }
    .toolbar {
      ToolbarItem {
        Button {
          withAnimation {
            $timestamps.withLock {
              $0.append(Timestamp(id: UUID(), value: Date()))
            }
          }
        } label: {
          Image(systemName: "plus")
        }
      }
    }

    if !timestamps.isEmpty {
      Section {
        ForEach(timestamps) { timestamp in
          Text(timestamp.value, format: Date.FormatStyle(date: .numeric, time: .standard))
        }
        .onDelete { indexSet in
          $timestamps.withLock {
            $0.remove(atOffsets: indexSet)
          }
        }
      } header: {
        Text("Timestamps")
      }
    }
  }
}

#Preview {
  NavigationStack {
    CaseStudyView {
      FileStorageSharedState()
    }
  }
}
