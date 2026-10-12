//
//  GameDefaultViewController.swift
//  GameDefault
//
//  Created by Dmytro Piankov on 2018. 07. 20..
//  Copyright © 2018. Dmytro Piankov. All rights reserved.
//

import Foundation
import UIKit
import GoogleMobileAds

class GameDefaultViewController: BaseViewController, GameViewController {

    fileprivate enum Constants {
        static let bottomSectionInset: CGFloat = 5
        static let animationDuration: Double = 1
        static let animationDelay: Double = 0.25
        static let okButtonTitle = "OK"
        static let shareButtonTitle = "SHARE"
        static let shareTitle = "Here we go"
        static let adUnitID = "ca-app-pub-3940256099942544/2934735716"
    }

    var presenter: GamePresenter?

    @IBOutlet weak var gameCollectionView: UICollectionView!
    @IBOutlet weak var turnLabel: LTMorphingLabel!
    @IBOutlet weak var bannerView: GADBannerView!

    var gameBoard: GameBoard? {
        didSet {
            self.gameCollectionView.reloadData()
        }
    }

    func updateTurnUI(message: String) {

        let effectValue = Int(arc4random_uniform(UInt32(LTMorphingEffect.allValues.count)))
        
        if let effect = LTMorphingEffect(rawValue: effectValue) {
            self.turnLabel.morphingEffect = effect
        }

        self.turnLabel.text = message
    }

    func showGameOver(title: String, handler: @escaping (() -> ())) {

        self.presenter?.resetData()

        let alert = UIAlertController(title: title, message: nil, preferredStyle: .alert)

        let okAction = UIAlertAction(title: Constants.okButtonTitle, style: .default, handler: { action in
            handler()
        })

        let shareAction = UIAlertAction(title: Constants.shareButtonTitle, style: .default, handler: { action in

            if let snapshot = self.navigationController?.view.snapshot {
                let activityViewController = UIActivityViewController(activityItems: [Constants.shareTitle, snapshot], applicationActivities: nil)
                activityViewController.completionWithItemsHandler = { activity, success, items, error in
                    handler()
                }
                self.present(activityViewController, animated: true, completion: nil)
            }
        })

        alert.addAction(okAction)
        alert.addAction(shareAction)

        self.present(alert, animated: true, completion: nil)
    }

    override func viewDidLoad() {
        super.viewDidLoad()

        self.presenter?.loadData()

        self.bannerView.adUnitID = Constants.adUnitID
        self.bannerView.load(GADRequest())

    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        self.showStartAnimation()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)

        if self.isMovingFromParentViewController {
            self.presenter?.resetData()
        }
    }

    func showStartAnimation() {
        self.gameCollectionView.transform = CGAffineTransform(scaleX: 0, y: 0)

        UIView.animate(withDuration: Constants.animationDuration, delay: Constants.animationDelay, options: UIViewAnimationOptions.curveEaseOut, animations: {
            self.gameCollectionView.transform = .identity
        }, completion: nil)
    }
}

// MARK: - UICollectionViewDataSource
extension GameDefaultViewController: UICollectionViewDataSource {

    func numberOfSections(in collectionView: UICollectionView) -> Int {
        return self.gameBoard?.numberOfSections ?? 0
    }

    public func collectionView(_ collectionView: UICollectionView, numberOfItemsInSection section: Int) -> Int {
        return self.gameBoard?.numberOfItemsInSection ?? 0
    }

    public func collectionView(_ collectionView: UICollectionView, cellForItemAt indexPath: IndexPath) -> UICollectionViewCell {

        let cell = collectionView.dequeueReusableCell(withReuseIdentifier: GameCollectionViewCell.defaultReuseIdentifier, for: indexPath) as! GameCollectionViewCell

        self.gameBoard.map{
            cell.imageView.image = ImageProvider.shared.image(name: $0.imageName(indexPath: indexPath))
        }

        return cell
    }
}

// MARK: - UICollectionViewDelegate
extension GameDefaultViewController: UICollectionViewDelegate {

    func collectionView(_ collectionView: UICollectionView, shouldSelectItemAt indexPath: IndexPath) -> Bool {
        return self.gameBoard?.canSelect(indexPath: indexPath) ?? false
    }

    public func collectionView(_ collectionView: UICollectionView, didSelectItemAt indexPath: IndexPath) {
        self.presenter?.selectData(indexPath: indexPath)
    }
}

// MARK: - UICollectionViewDelegateFlowLayout
extension GameDefaultViewController: UICollectionViewDelegateFlowLayout {
    func collectionView(_ collectionView: UICollectionView, layout collectionViewLayout: UICollectionViewLayout, insetForSectionAt section: Int) -> UIEdgeInsets {

        guard let gameBoard = self.gameBoard, (section != gameBoard.numberOfSections - 1) else {
            return UIEdgeInsets.zero
        }

        return UIEdgeInsetsMake(0, 0, Constants.bottomSectionInset, 0)
    }
}


