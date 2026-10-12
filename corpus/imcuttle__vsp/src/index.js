/**
 * @file index
 * @author Cuttle Cong
 * @date 2018/5/10
 * @description
 */
import * as u from 'url'
import * as qs from 'querystring'
import md5 from 'md5'
import CircularJSON from 'circular-json'
import persistLocalStorage from './persistence/localStorage'

const debug = require('debug')('vsp')

function appendUrlQueryString(url, appendQuery) {
  let obj = u.parse(url, false)
  if (obj.hash) {
    let i = obj.hash.lastIndexOf('?')
    let queryString = ''
    let query = {}
    if (i >= 0) {
      queryString = obj.hash.slice(i + 1)
      query = qs.parse(queryString)
    }
    else {
      i = obj.hash.length
    }
    Object.assign(query, appendQuery)
    obj.hash = obj.hash.slice(0, i) + '?' + qs.stringify(query)
  }
  delete obj.search
  return u.format(obj)
}

function removeUrlQueryString(url, keys = []) {
  let obj = u.parse(url, false)
  if (obj.hash) {
    let i = obj.hash.lastIndexOf('?')
    let queryString = ''
    if (i >= 0) {
      queryString = obj.hash.slice(i + 1)
      let query = qs.parse(queryString)

      keys.forEach(key => {
        delete query[key]
      })
      obj.hash = obj.hash.slice(0, i) + '?' + qs.stringify(query)
    }
  }
  delete obj.search
  return u.format(obj)
}

export class VSP {
  constructor() {
    // browser hash URL client
    this.client = {
      getUid() {
        let obj = u.parse(location.href, true)
        if (obj.hash) {
          let i = obj.hash.lastIndexOf('?')
          let queryString = ''
          if (i >= 0) {
            queryString = obj.hash.slice(i + 1)
            let query = qs.parse(queryString)

            this.removeUid()

            return query.vsp_uid
          }
        }
      },
      removeUid() {
        location.replace(removeUrlQueryString(location.href, ['vsp_uid']))
      },
      generateShared(uid) {
        return appendUrlQueryString(location.href, { vsp_uid: uid })
      }
    }

    this.persistence = persistLocalStorage()
  }
  setStore(store) {
    this.store = store
  }
  setPersistence(persistence) {
    this.persistence = persistence
  }
  async run() {
    const { persistence, store } = this
    debug('run vsp: %O.', this)
    let uid = this.client.getUid()
    if (uid) {
      debug('Matched uid: %s.', uid)
      let store = await persistence.fetch(uid)
      debug('Fetched store: %O.', store)
      store && this.setUpStore(store)
    }
  }

  generateUid(store) {
    return md5(CircularJSON.stringify(store))
  }

  async generateShared() {
    if (!this.store) {
      return
    }
    let uid = this.generateUid(this.store)
    debug('generate uid: %s.', uid)
    await this.persistence.save(uid, this.store)
    const shared = await this.client.generateShared(uid)
    debug('generate shared: %s form store: %o.', shared, this.store)

    return shared
  }

  setUpStore(store) {

  }
}

export default function vsp() {
  return new VSP()
}
