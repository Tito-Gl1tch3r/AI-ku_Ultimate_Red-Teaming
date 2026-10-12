//
//  GameDefaultPresenter.swift
//  GameDefault
//
//  Created by Dmytro Piankov on 2018. 07. 20..
//  Copyright © 2018. Dmytro Piankov. All rights reserved.
//

import Foundation

class GameDefaultPresenter: GamePresenter {

    fileprivate enum Constants {
        static let drawMessage = "A draw"
        static let turnMessage = "'s turn"
        static let winMessage = " wins"
    }

    var router: GameRouter?
    var interactor: GameInteractor?
    weak var view: GameViewController?

    var xmarkFirstGame: Bool

    init(xmarkFirstGame: Bool) {
        self.xmarkFirstGame = xmarkFirstGame
    }

    func loadData() {
        let gameBoard = self.interactor?.gameBoard(xmarkFirstGame: self.xmarkFirstGame)
        self.view?.gameBoard = gameBoard
        self.view?.updateTurnUI(message: self.nextMoveMessage())
    }

    func resetData() {
        self.interactor?.resetGame()
    }

    func selectData(indexPath: IndexPath) {

        guard let interactor = self.interactor else {
            return
        }

        let result = interactor.makeMove(indexPath: indexPath)
        self.view?.gameBoard = result.board

        guard !result.isGameFinished else {
            let title = result.isDraw ? Constants.drawMessage : "\(interactor.currentPlayerName())" + Constants.winMessage
            self.view?.showGameOver(title: title, handler: {
                self.router?.routeForEndGame()
            })
            return
        }

        self.view?.updateTurnUI(message: self.nextMoveMessage())
    }

    private func nextMoveMessage() -> String {

        guard let interactor = self.interactor else {
            return ""
        }
        return "\(interactor.currentPlayerName())" + Constants.turnMessage
    }
}
