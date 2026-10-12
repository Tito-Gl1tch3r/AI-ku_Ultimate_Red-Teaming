//
//  AppDelegate.swift
//  TicTacToe
//
//  Created by Dmytro Piankov on 7/20/18.
//  Copyright © 2018 Dmytro Piankov. All rights reserved.
//

import UIKit
import GoogleMobileAds

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {

    private enum Constants {
        static let mobileAdsAppId = "ca-app-pub-5462745479472047~8226420093"
    }

    var window: UIWindow?

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplicationLaunchOptionsKey: Any]?) -> Bool {

        ImageProvider.shared.preloadImages()
        GADMobileAds.configure(withApplicationID: Constants.mobileAdsAppId)

        return true
    }

    func applicationDidEnterBackground(_ application: UIApplication) {
        guard Game.shared.isGameInProgress else {
            return
        }
        GameSaver().saveGame(game: Game.shared)
    }
}

