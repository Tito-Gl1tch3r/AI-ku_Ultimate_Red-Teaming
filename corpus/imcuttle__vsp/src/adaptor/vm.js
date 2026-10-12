/**
 * @file vm
 * @author Cuttle Cong
 * @date 2018/5/10
 * @description
 */

import * as React from 'react'
import { isViewModelComponent, Root } from 'react-mobx-vm'

const debug = require('debug')('vsp:vm')

// vm(AppContainer)
export default function VMVSPSourceAdaptor(vsp) {
  return function vm(AppContainer) {

    function _update() {
      const data = [this.props.local]
      React.Children.toArray(this.props.children).forEach(child => {
        let isVMComp = child && isViewModelComponent(child.type)
        if (isVMComp && child.props.local) {
          data.push(child.props.local)
        }
      })

      debug('vm-store: %o', data)
      // VM instance
      vsp.setStore(data)
      vsp.setUpStore = store => {
        if (Array.isArray(store)) {
          store.forEach((eachStore, i) => {
            if (data[i] && (data[i] instanceof Root)) {
              data[i].assign(eachStore)
            }
          })
        }
      }
    }

    return class VSPAppContainer extends AppContainer {
      static displayName = `VSP_${AppContainer.displayName ||
        AppContainer.name ||
        ''}`

      componentDidUpdate() {
        super.componentDidUpdate && super.componentDidUpdate.apply(this, arguments)
        _update.call(this)
      }

      componentDidMount() {
        super.componentDidMount && super.componentDidMount.apply(this, arguments)
        _update.call(this)
        vsp.run()
      }
    }
  }
}
