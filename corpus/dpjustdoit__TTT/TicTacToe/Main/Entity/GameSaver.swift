//
//  GameSaver.swift
//  TicTacToe
//
//  Created by Dmytro Piankov on 7/23/18.
//  Copyright © 2018 Dmytro Piankov. All rights reserved.
//

import Foundation

extension String {
    func appendingPathComponent(_ string: String) -> String {
        return URL(fileURLWithPath: self).appendingPathComponent(string).path
    }
}

struct GameSaver {

    fileprivate enum Constants {
        static let gameKey = "game"
    }

    let gamePathString = NSSearchPathForDirectoriesInDomains(.documentDirectory, .userDomainMask, true).first!.appendingPathComponent(Constants.gameKey)

    func saveGame(game: Game) {

        do {
            let data = try PropertyListEncoder().encode(game)
            let success = NSKeyedArchiver.archiveRootObject(data, toFile: self.gamePathString)
            print(success ? "Successful save" : "Save Failed")
        } catch {
            print("Save Failed")
        }
    }

    func restoreGame() -> Game? {

        guard let data = NSKeyedUnarchiver.unarchiveObject(withFile: self.gamePathString) as? Data else { return nil }
        do {
            let game = try PropertyListDecoder().decode(Game.self, from: data)
            return game
        } catch {
            print("Retrieve Failed")
            return nil
        }
    }

    func clearSaves() {
        do {
            try FileManager.default.removeItem(atPath: self.gamePathString)
        } catch {
            print("Clean Failed")
        }
    }
}
