//
//  ImageProvider.swift
//  TicTacToe
//
//  Created by Dmytro Piankov on 7/23/18.
//  Copyright © 2018 Dmytro Piankov. All rights reserved.
//

import Foundation
import UIKit

struct ImageProvider {

    static let shared: ImageProvider = ImageProvider()

    enum Constants {
        static let xImageName = "x_mark"
        static let oImageName = "o_mark"
    }

    private let imageCache = NSCache<NSString, UIImage>()

    func preloadImages() {
        self.preloadImage(name: Constants.xImageName)
        self.preloadImage(name: Constants.oImageName)
    }

    func image(name: String) -> UIImage? {

        guard !name.isEmpty else {
            return nil
        }

        guard let image = self.imageCache.object(forKey: name as NSString) else {
            return UIImage(named: name)
        }

        return image
    }

    private func preloadImage(name: String) {

        guard !name.isEmpty, let url = URL(string: ("http://d.michd.me/aa-lab/" + name + ".png")) else {
            return
        }

        URLSession.shared.dataTask(with: url) { data, response, error in
            guard
                let httpURLResponse = response as? HTTPURLResponse, httpURLResponse.statusCode == 200,
                let mimeType = response?.mimeType, mimeType.hasPrefix("image"),
                let data = data, error == nil,
                let image = UIImage(data: data) else {
                    return
            }

            self.imageCache.setObject(image, forKey: name as NSString)

            }.resume()
    }
}
