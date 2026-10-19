from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Account
from app.schemas import AccountCreate, AccountUpdate, AccountOut

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])

@router.get("", response_model=List[AccountOut])
def list_accounts(platform: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Account)
    if platform:
        query = query.filter(Account.platform == platform.lower())
    accounts = query.order_by(Account.created_at.desc()).all()
    
    # Mapeo a DTO seguro (no exponemos el access_token completo al cliente)
    results = []
    for acc in accounts:
        results.append(AccountOut(
            id=acc.id,
            platform=acc.platform,
            account_name=acc.account_name,
            platform_user_id=acc.platform_user_id,
            is_active=acc.is_active,
            has_valid_token=bool(acc.access_token),
            token_expires_at=acc.token_expires_at,
            created_at=acc.created_at
        ))
    return results

@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(account_in: AccountCreate, db: Session = Depends(get_db)):
    new_account = Account(
        platform=account_in.platform.lower(),
        account_name=account_in.account_name,
        platform_user_id=account_in.platform_user_id,
        access_token=account_in.access_token,
        refresh_token=account_in.refresh_token,
        token_expires_at=account_in.token_expires_at,
        extra_data=account_in.extra_data,
        is_active=account_in.is_active
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return AccountOut(
        id=new_account.id,
        platform=new_account.platform,
        account_name=new_account.account_name,
        platform_user_id=new_account.platform_user_id,
        is_active=new_account.is_active,
        has_valid_token=bool(new_account.access_token),
        token_expires_at=new_account.token_expires_at,
        created_at=new_account.created_at
    )

@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return AccountOut(
        id=account.id,
        platform=account.platform,
        account_name=account.account_name,
        platform_user_id=account.platform_user_id,
        is_active=account.is_active,
        has_valid_token=bool(account.access_token),
        token_expires_at=account.token_expires_at,
        created_at=account.created_at
    )

@router.put("/{account_id}", response_model=AccountOut)
def update_account(account_id: int, update_data: AccountUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    if update_data.account_name is not None:
        account.account_name = update_data.account_name
    if update_data.is_active is not None:
        account.is_active = update_data.is_active
    if update_data.access_token is not None:
        account.access_token = update_data.access_token
    if update_data.refresh_token is not None:
        account.refresh_token = update_data.refresh_token
        
    db.commit()
    db.refresh(account)
    return AccountOut(
        id=account.id,
        platform=account.platform,
        account_name=account.account_name,
        platform_user_id=account.platform_user_id,
        is_active=account.is_active,
        has_valid_token=bool(account.access_token),
        token_expires_at=account.token_expires_at,
        created_at=account.created_at
    )

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    db.delete(account)
    db.commit()
    return None
