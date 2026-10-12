package com.finedjentleman.routinetracker.services;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.finedjentleman.routinetracker.models.User;
import com.finedjentleman.routinetracker.repositories.UserRepository;

@Service
public class UserServiceImpl implements UserService {

	@Autowired
	UserRepository userRepository;
	
	@Override
	public void addUser(User user) {
		
		userRepository.save(user);
		
	}
	
	@Override
	public User getUser(Long userId) {
		
		return userRepository.getOne(userId);
		
	}
	
	@Override
	public void deleteUser(Long userId) {
		
		userRepository.deleteById(userId);
		
	}
}
