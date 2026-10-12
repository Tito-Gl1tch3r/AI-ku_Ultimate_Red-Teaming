//
//  GameDefaultInteractor.swift
//  GameDefault
//
//  Created by Dmytro Piankov on 2018. 07. 20..
//  Copyright © 2018. Dmytro Piankov. All rights reserved.
//

import Foundation
import UIKit

typealias GameResult = (isGameFinished: Bool, isDraw: Bool, board: GameBoard)

class GameDefaultInteractor: GameInteractor {

    fileprivate enum Constants {
        static let xplayerName = "X"
        static let oplayerName = "O"
    }

    weak var presenter: GamePresenter?

    func gameBoard(xmarkFirstGame: Bool) -> GameBoard {

        guard !Game.shared.isGameInProgress else {
            return Game.shared.board
        }
        
        let firstPlayer = xmarkFirstGame ? Player(playerName: Constants.xplayerName,
                                                  imageName: ImageProvider.Constants.xImageName,
                                                  positions: []) : Player(playerName: Constants.oplayerName,
                                                                          imageName: ImageProvider.Constants.oImageName,
                                                                          positions: [])
        let secondPlayer =  xmarkFirstGame ? Player(playerName: Constants.oplayerName,
                                                    imageName: ImageProvider.Constants.oImageName,
                                                    positions: []) : Player(playerName: Constants.xplayerName,
                                                                            imageName: ImageProvider.Constants.xImageName,
                                                                            positions: [])
        Game.shared.players = [firstPlayer, secondPlayer]

        return Game.shared.board
    }

    func currentPlayerName() -> String {
        return Game.shared.currentPlayer.playerName
    }

    func resetGame() {
        Game.shared.reset()
    }

    func makeMove(indexPath: IndexPath) -> GameResult {
        let isGameFinished = Game.shared.currentPlayerMove(indexPath: indexPath)
        return (isGameFinished, Game.shared.isDraw, Game.shared.board)
    }
}
