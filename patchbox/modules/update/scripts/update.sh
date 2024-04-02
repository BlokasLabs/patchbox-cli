#!/bin/sh

install_repo() {
	GIT="git -c user.name=\"apt-get\" -c user.email=\"apt@get\""
	if [ ! -d "$3" ]; then
		echo "Cloning $1 repository from $2..."
		$GIT clone "$2" "$3" --branch $4
	else
		echo "Updating $1 repository with latest stuff in $2..."
		cd $3 && $GIT stash && $GIT fetch --all && $GIT checkout $4 && $GIT merge --ff-only
	fi
}

install_repo patchbox-modules https://github.com/BlokasLabs/patchbox-modules /usr/local/patchbox-modules bookworm

apt-get update
apt-get install patchbox patchbox-cli -y
