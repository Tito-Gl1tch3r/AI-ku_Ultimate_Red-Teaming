//
//  Game.swift
//  TicTacToe
//
//  Created by Dmytro Piankov on 7/20/18.
//  Copyright © 2018 Dmytro Piankov. All rights reserved.
//

import Foundation

class Game: Codable {

    static let shared: Game = {

        guard let game = GameSaver().restoreGame() else {
            return Game(boardSize: 3)
        }

        return game
    }()

    let boardSize: Int
    var players: [Player] = []
    var isDraw: Bool = false
    private var currentPlayerIndex: Int = 0

    var board: Board

    var isGameInProgress: Bool {
        return !self.players.isEmpty
    }

    var currentPlayer: Player {
        return self.players[currentPlayerIndex]
    }

    func currentPlayerMove(indexPath: IndexPath) -> Bool  {

        self.players[currentPlayerIndex].positions.append(indexPath)
        self.board.setValue(value: self.currentPlayer.imageName, indexPath: indexPath)

        guard !self.checkWinner(indexPath: indexPath) else {
            return true
        }

        self.currentPlayerIndex = (self.currentPlayerIndex == 0) ? 1 : 0
        return false
    }

    func reset() {
        self.players = []
        self.isDraw = false
        self.currentPlayerIndex = 0
        self.board = Board(size: self.boardSize)
        GameSaver().clearSaves()
    }

    private func checkWinner(indexPath: IndexPath) -> Bool {

        //Row
        for item in 0..<self.boardSize {
            guard self.board.value(indexPath: IndexPath(item: item, section: indexPath.section)) == self.currentPlayer.imageName else {
                break
            }

            guard item != (self.boardSize - 1) else {
                return true
            }
        }

        //Column
        for section in 0..<self.boardSize {
            guard self.board.value(indexPath: IndexPath(item: indexPath.item, section: section)) == self.currentPlayer.imageName else {
                break
            }

            guard section != (self.boardSize - 1) else {
                return true
            }
        }

        //Diagonal
        if indexPath.row == indexPath.section {
            for index in 0..<self.boardSize {
                guard self.board.value(indexPath: IndexPath(item: index, section: index)) == self.currentPlayer.imageName else {
                    break
                }

                guard index != (self.boardSize - 1) else {
                    return true
                }
            }
        }

        //AntiDiagonal
        if (indexPath.row + indexPath.section) == (self.boardSize - 1) {
            for index in 0..<self.boardSize {
                guard self.board.value(indexPath: IndexPath(item: index, section: (self.boardSize - 1) - index)) == self.currentPlayer.imageName else {
                    break
                }

                guard index != (self.boardSize - 1) else {
                    return true
                }
            }
        }

        // Draw
        let movesCount = self.players.reduce(0) { (result, player) -> Int in
            return result + player.positions.count
        }
        if movesCount == self.boardSize * self.boardSize {
            self.isDraw = true
            return true
        }

        return false
    }

    init(boardSize: Int) {
        self.boardSize = boardSize
        self.board = Board(size: self.boardSize)
    }
}




