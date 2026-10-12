//
//  ViewController.swift
//  UserDefaults Example
//
//  Created by Mehrdad on 2021-03-11.
//  Copyright © 2021 Udacity. All rights reserved.
//

import Foundation
import UIKit

class ViewController: UIViewController {
    
    // MARK: - Outlets
    @IBOutlet weak var titleLabel: UILabel!
    @IBOutlet weak var themeLabel: UILabel!
    @IBOutlet weak var themeSwitch: UISwitch!
    

    override func viewDidLoad() {
        super.viewDidLoad()
        
        if let weWantMidnight = UserDefaults.standard.object(forKey: "MidnightThemeOn") {
            if weWantMidnight as! Bool {
                    switchToMidnight()
                } else {
                    switchToDaylight()
                }
        }
        
    }
    
    
    // MARK: - Actions
    @IBAction func switchToMidnight(_ sender: UISwitch) {
        if sender.isOn {
            switchToMidnight()
        } else {
            switchToDaylight()
        }
    }
    
    
    
    // MARK: - Helper Methods
    
    func switchToMidnight() {
        themeLabel.text = "Midnight Theme"
        themeLabel.textColor = UIColor.white
        titleLabel.textColor = UIColor.white
        view.backgroundColor = UIColor.midnight
        UserDefaults.standard.set(true, forKey: "MidnightThemeOn")
        themeSwitch.isOn = true
        
    }
    
    func switchToDaylight() {
        themeLabel.text = "Daylight Theme"
        themeLabel.textColor = UIColor.black
        titleLabel.textColor = UIColor.black
        view.backgroundColor = UIColor.daylight
        UserDefaults.standard.set(false, forKey: "MidnightThemeOn")
        themeSwitch.isOn = false
    }

}

