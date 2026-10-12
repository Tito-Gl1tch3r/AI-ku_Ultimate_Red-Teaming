import Sharing
import UIKit
import UIKitNavigation

final class SharedStateInViewController: UIViewController, UIKitCaseStudy {
  let caseStudyTitle = "Shared state in UIKit view controller"
  let caseStudyNavigationTitle = "In UIKit"
  let readMe = """
    Demonstrates how to use a `@Shared` value directly in a UIKit view controller.
    """

  @Shared(.appStorage("count")) var count = 0

  override func viewDidLoad() {
    super.viewDidLoad()

    let countLabel = UILabel()

    let incrementButton = UIButton(type: .system)
    incrementButton.setTitle("Increment", for: .normal)
    incrementButton.addAction(
      UIAction { [weak self] _ in
        self?.$count.withLock { $0 += 1 }
      },
      for: .touchUpInside
    )
    let decrementButton = UIButton(type: .system)
    decrementButton.setTitle("Decrement", for: .normal)
    decrementButton.addAction(
      UIAction { [weak self] _ in
        self?.$count.withLock { $0 -= 1 }
      },
      for: .touchUpInside
    )
    let stackView = UIStackView(arrangedSubviews: [
      countLabel,
      incrementButton,
      decrementButton,
    ])
    stackView.alignment = .center
    stackView.axis = .vertical
    stackView.translatesAutoresizingMaskIntoConstraints = false
    view.addSubview(stackView)

    NSLayoutConstraint.activate([
      stackView.centerXAnchor.constraint(equalTo: view.centerXAnchor),
      stackView.centerYAnchor.constraint(equalTo: view.centerYAnchor),
    ])

    observe { [weak self] in
      guard let self else { return }

      countLabel.text = count.description
    }
  }
}

#Preview {
  SharedStateInViewController()
}
